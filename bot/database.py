import sqlite3
import logging
import os
import shutil
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager
import pytz
import json
from config import DB_PATH, SCHEMA_PATH
from bot.constants import DEFAULT_NOTIFICATION_SETTINGS, DEFAULT_NOTIFICATION_TEMPLATES

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.db_path = DB_PATH
        self.backup_dir = os.path.join(os.path.dirname(self.db_path), "backups")
        self._ensure_data_directory()
        self._init_db()

    def _ensure_data_directory(self):
        """Создание директорий для данных и резервных копий"""
        # Убеждаемся, что основная директория data существует
        data_dir = os.path.dirname(self.db_path)
        if not os.path.exists(data_dir):
            raise FileNotFoundError(f"Директория данных {data_dir} не найдена!")
        os.makedirs(data_dir, exist_ok=True)

        # Создаем директорию для резервных копий внутри data
        os.makedirs(self.backup_dir, exist_ok=True)

        logger.info(f"Проверка наличия директории данных: {data_dir}")
        logger.info(f"Проверка наличия директории резервных копий: {self.backup_dir}")

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {str(e)}")
            raise e
        finally:
            conn.close()

    def _init_db(self):
        """Инициализация базы данных"""
        try:
            logger.info(f"Инициализация базы данных: {self.db_path}")

            # Проверяем существование файла схемы
            if not os.path.exists(SCHEMA_PATH):
                raise FileNotFoundError(f"Файл схемы {SCHEMA_PATH} не найден!")

            # Проверяем существование базы данных
            db_exists = os.path.exists(self.db_path)

            # Создаем соединение с базой данных (создает файл если его нет)
            with self.get_connection() as conn:
                if not db_exists:
                    logger.info("Создание новой базы данных")
                    # Читаем и выполняем SQL-схему
                    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
                        schema = f.read()

                    # Выполняем каждый SQL-запрос отдельно
                    for statement in schema.split(';'):
                        if statement.strip():
                            conn.execute(statement)

                    # Инициализация базовых настроек
                    self._init_default_settings()

                logger.info("База данных успешно инициализирована")

        except FileNotFoundError as e:
            logger.error(f"Файл схемы не найден: {str(e)}")
            raise
    
        except Exception as e:
            logger.error(f"Ошибка инициализации базы данных: {str(e)}")
            raise

    def _init_default_settings(self):
        """Инициализация настроек по умолчанию"""
        try:
            with self.get_connection() as conn:
                # Проверяем существование таблицы notification_templates
                conn.execute("""
                CREATE TABLE IF NOT EXISTS notification_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    template TEXT NOT NULL,
                    category TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
                
                # Проверяем существование таблицы notification_settings
                conn.execute("""
                CREATE TABLE IF NOT EXISTS notification_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_id INTEGER NOT NULL,
                    days_before INTEGER NOT NULL,
                    time TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (template_id) REFERENCES notification_templates(id)
                )
            """)

                # Добавляем шаблоны уведомлений по умолчанию
                template_ids = {}
                for template_data in DEFAULT_NOTIFICATION_TEMPLATES:
                    # Проверяем существование шаблона
                    existing_template = conn.execute("""
                        SELECT id FROM notification_templates 
                        WHERE name = ? AND category = ?
                    """, (template_data['name'], template_data['category'])).fetchone()

                    if existing_template:
                        template_ids[template_data['name']] = existing_template['id']
                    else:
                        cursor = conn.execute("""
                            INSERT INTO notification_templates (name, template, category)
                            VALUES (?, ?, ?)
                        """, (template_data['name'], template_data['template'], template_data['category']))
                        template_ids[template_data['name']] = cursor.lastrowid

                # Добавляем настройки уведомлений
                for setting in DEFAULT_NOTIFICATION_SETTINGS:
                    template_id = template_ids.get(setting['template_name'])
                    if not template_id:
                        continue
                    
                    # Проверяем существование настройки
                    exists = conn.execute("""
                        SELECT COUNT(*) FROM notification_settings 
                        WHERE template_id = ? AND days_before = ? AND time = ?
                    """, (template_id, setting['days_before'], setting['time'])).fetchone()[0]

                    if not exists:
                        conn.execute("""
                            INSERT INTO notification_settings (template_id, days_before, time)
                            VALUES (?, ?, ?)
                        """, (template_id, setting['days_before'], setting['time']))

                logger.info("Настройки по умолчанию успешно добавлены")

        except Exception as e:
            logger.error(f"Ошибка инициализации настроек: {str(e)}")
            raise

    def get_max_days_before(self) -> int:
        """
        Получить максимальное значение days_before из активных настроек уведомлений.

        Returns:
            int: Максимальное количество дней для предварительных уведомлений
        """
        try:
            with self.get_connection() as conn:
                result = conn.execute("""
                    SELECT MAX(days_before) as max_days
                    FROM notification_settings
                    WHERE is_active = 1
                """).fetchone()

                max_days = result['max_days'] if result and result['max_days'] is not None else 0
                logger.info(f"Максимальное количество дней для уведомлений: {max_days}")
                return max_days

        except Exception as e:
            logger.error(f"Ошибка получения максимального количества дней: {str(e)}")
            return 0    
    
    def get_upcoming_birthdays(self, days_ahead: int = None) -> List[Dict]:
        """
        Получить дни рождения для конкретной даты или диапазона дат.

        Args:
            days_ahead: Через сколько дней будет день рождения. 
                       Если None, возвращает все дни рождения в диапазоне [сегодня, сегодня + макс_дней]

        Returns:
            List[Dict]: Список пользователей с их днями рождения
        """
        try:
            # Получаем текущую дату в московском времени
            moscow_tz = pytz.timezone('Europe/Moscow')
            current_date = datetime.now(moscow_tz).date()

            with self.get_connection() as conn:
                if days_ahead is not None:
                    # Для конкретной даты
                    target_date = current_date + timedelta(days=days_ahead)
                    query = """
                        SELECT * FROM users 
                        WHERE strftime('%m-%d', birth_date) = strftime('%m-%d', ?)
                        AND is_subscribed = 1
                    """
                    params = (target_date.strftime("%Y-%m-%d"),)

                else:
                    # Для диапазона дат
                    max_days = self.get_max_days_before()
                    if max_days == 0:
                        return []

                    target_date = current_date + timedelta(days=max_days)
                    current_md = current_date.strftime("%m-%d")
                    target_md = target_date.strftime("%m-%d")

                    if current_md <= target_md:
                        query = """
                            SELECT * FROM users 
                            WHERE strftime('%m-%d', birth_date) BETWEEN ? AND ?
                            AND is_subscribed = 1
                        """
                        params = (current_md, target_md)
                    else:
                        # Обработка перехода через год
                        query = """
                            SELECT * FROM users 
                            WHERE (strftime('%m-%d', birth_date) >= ? 
                                  OR strftime('%m-%d', birth_date) <= ?)
                            AND is_subscribed = 1
                        """
                        params = (current_md, target_md)

                results = conn.execute(query, params).fetchall()
                birthdays = [dict(row) for row in results]

                if days_ahead is not None:
                    logger.info(f"Найдено {len(birthdays)} дней рождения на дату {target_date.strftime('%d.%m.%Y')}")
                else:
                    logger.info(f"Найдено {len(birthdays)} дней рождения в диапазоне {current_md} — {target_md}")

                return birthdays

        except Exception as e:
            logger.error(f"Ошибка получения предстоящих дней рождения: {str(e)}")
            return []

    def get_notification_settings(self) -> List[Dict]:
        """Get all notification settings with their templates"""
        try:
            with self.get_connection() as conn:
                results = conn.execute("""
                    SELECT ns.*, nt.name as template_name, nt.template
                    FROM notification_settings ns
                    JOIN notification_templates nt ON ns.template_id = nt.id
                    WHERE ns.is_active = 1 
                    AND nt.is_active = 1
                    ORDER BY ns.days_before DESC, ns.time
                """).fetchall()

                settings = [dict(row) for row in results]
                logger.info(f"Retrieved {len(settings)} active notification settings")
                return settings

        except Exception as e:
            logger.error(f"Error getting notification settings: {str(e)}")
            return []

    def add_user(self, telegram_id: int, username: str, first_name: str, 
                last_name: str, birth_date: str, is_subscribed: bool) -> bool:
        """Добавление нового пользователя в базу данных"""
        try:
            with self.get_connection() as conn:
                # Проверяем существование таблицы users
                conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT NOT NULL,
                    last_name TEXT,
                    birth_date TEXT NOT NULL,
                    is_admin BOOLEAN DEFAULT 0,
                    is_subscribed BOOLEAN DEFAULT 0,
                    is_notifications_enabled BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
                
                conn.execute("""
                    INSERT INTO users (telegram_id, username, first_name, last_name, birth_date, is_subscribed)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (telegram_id, username, first_name, last_name, birth_date, is_subscribed))
                return True
        except Exception as e:
            logger.error(f"Error adding user: {str(e)}")
            return False

    def delete_user(self, telegram_id: int) -> bool:
        """Delete user from database"""
        try:
            with self.get_connection() as conn:
                conn.execute("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))
                return True
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            return False

    def update_user(self, telegram_id: int, **kwargs) -> bool:
        """Update user information"""
        try:
            with self.get_connection() as conn:
                update_fields = []
                values = []
                for key, value in kwargs.items():
                    if key in ['first_name', 'last_name', 'birth_date', 'is_admin', 'is_subscribed']:
                        update_fields.append(f"{key} = ?")
                        values.append(value)

                if not update_fields:
                    return False

                values.append(telegram_id)
                query = f"""
                    UPDATE users 
                    SET {', '.join(update_fields)}
                    WHERE telegram_id = ?
                """
                conn.execute(query, values)
                return True

        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            return False

    def get_all_users_except(self, exclude_telegram_id: int) -> List[Dict]:
        """Get all users except specified one"""
        try:
            with self.get_connection() as conn:
                results = conn.execute("""
                    SELECT * FROM users 
                    WHERE telegram_id != ? 
                    AND is_subscribed = 1
                """, (exclude_telegram_id,)).fetchall()
                return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Error getting users list: {str(e)}")
            return []

    def get_user(self, telegram_id: int) -> Optional[Dict]:
        """Get user by telegram ID"""
        try:
            with self.get_connection() as conn:
                result = conn.execute("""
                    SELECT * FROM users 
                    WHERE telegram_id = ?
                """, (telegram_id,)).fetchone()
                return dict(result) if result else None

        except Exception as e:
            logger.error(f"Error getting user: {str(e)}")
            return None

    def log_notification(self, user_id: int, message_text: str, status: str, error_message: Optional[str] = None):
        """Log notification details"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO notification_logs (user_id, message_text, status, error_message)
                    VALUES (?, ?, ?, ?)
                """, (user_id, message_text, status, error_message))
                logger.info(f"Notification logged for user {user_id}")

        except Exception as e:
            logger.error(f"Error logging notification: {str(e)}")

    def create_backup(self) -> Optional[str]:
        """Create database backup"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"birthday_bot_{timestamp}.db"
            backup_path = os.path.join(self.backup_dir, backup_name)

            # Проверяем существование директории для резервных копий
            if not os.path.exists(self.backup_dir):
                os.makedirs(self.backup_dir)
            
            # Создаем резервную копию
            with self.get_connection() as conn:
                backup = sqlite3.connect(backup_path)
                conn.backup(backup)
                backup.close()
            
            logger.info(f"Резервная копия базы данных создана: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Ошибка создания резервной копии: {str(e)}")
            return None

    def list_backups(self) -> List[str]:
        """List available database backups"""
        try:
            backups = [f for f in os.listdir(self.backup_dir) if f.endswith('.db')]
            backups.sort(reverse=True)  # Most recent first
            return backups
        except Exception as e:
            logger.error(f"Error listing backups: {str(e)}")
            return []

    def restore_from_backup(self, backup_path: str) -> bool:
        """Restore database from backup"""
        if not os.path.exists(backup_path):
            logger.error(f"Backup file not found: {backup_path}")
            return False

        try:
            # Create a temporary backup of current database
            temp_backup = self.create_backup()
            
            # Restore from backup
            shutil.copy2(backup_path, self.db_path)
            logger.info(f"Database restored from backup: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error restoring from backup: {str(e)}")
            if temp_backup:
                try:
                    shutil.copy2(temp_backup, self.db_path)
                    logger.info("Restored from temporary backup after failed restore")
                except Exception as restore_error:
                    logger.error(f"Error restoring from temporary backup: {str(restore_error)}")
            return False

    def get_all_birthdays(self) -> List[Dict]:
        """Get all birthdays ordered by month and day"""
        try:
            with self.get_connection() as conn:
                results = conn.execute("""
                    SELECT * FROM users 
                    WHERE is_subscribed = 1
                    ORDER BY strftime('%m-%d', birth_date)
                """).fetchall()

                birthdays = [dict(row) for row in results]
                logger.info(f"Retrieved {len(birthdays)} birthdays from database")
                return birthdays

        except Exception as e:
            logger.error(f"Error getting all birthdays: {str(e)}")
            return []

    def update_user_subscription(self, telegram_id: int, is_subscribed: bool) -> bool:
        """Update user subscription status"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    UPDATE users 
                    SET is_subscribed = ?
                    WHERE telegram_id = ?
                """, (is_subscribed, telegram_id))

                # Проверяем, был ли пользователь обновлен
                result = conn.execute("""
                    SELECT changes() as updated_rows
                """).fetchone()

                success = result['updated_rows'] > 0
                logger.info(
                    f"User {telegram_id} subscription status updated to {is_subscribed}. "
                    f"Success: {success}"
                )
                return success

        except Exception as e:
            logger.error(f"Error updating user subscription: {str(e)}")
            return False
    
    def check_notification_setting_exists(self, days_before: int, time: str) -> bool:
        """Check if notification setting with given parameters already exists"""
        try:
            with self.get_connection() as conn:
                result = conn.execute("""
                    SELECT COUNT(*) as count
                    FROM notification_settings
                    WHERE days_before = ? AND time = ? AND is_active = 1
                """, (days_before, time)).fetchone()

                exists = result['count'] > 0
                if exists:
                    logger.info(f"Found existing notification setting for {days_before} days at {time}")
                return exists

        except Exception as e:
            logger.error(f"Error checking notification setting existence: {str(e)}")
            return False

    def add_notification_setting(self, template_id: int, days_before: int, time: str) -> Tuple[bool, Optional[int], str]:
        """Add new notification setting if it doesn't exist
        
        Returns:
            Tuple[bool, Optional[int], str]: (success, new_setting_id, message)
            where success indicates if operation was successful,
            new_setting_id is the ID of newly created setting (None if failed),
            and message contains status/error information
        """
        try:
            # Проверяем существование настройки
            if self.check_notification_setting_exists(days_before, time):
                return False, None, "Настройка уведомлений с такими параметрами уже существует"

            with self.get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO notification_settings (template_id, days_before, time)
                    VALUES (?, ?, ?)
                """, (template_id, days_before, time))

                new_setting_id = cursor.lastrowid

                logger.info(
                    f"Added notification setting: template_id={template_id}, "
                    f"days_before={days_before}, time={time}, id={new_setting_id}"
                )
                return True, new_setting_id, "Настройка уведомлений успешно добавлена"

        except Exception as e:
            error_msg = f"Error adding notification setting: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg

    def delete_notification_setting(self, setting_id: int) -> Tuple[bool, str]:
        """Delete notification setting by ID
        
        Returns:
            Tuple[bool, str]: (success, message) where success indicates if operation 
            was successful and message contains status/error information
        """
        try:
            with self.get_connection() as conn:
                # Проверяем существование настройки
                exists = conn.execute("""
                    SELECT COUNT(*) as count FROM notification_settings WHERE id = ?
                """, (setting_id,)).fetchone()['count'] > 0

                if not exists:
                    return False, "Настройка уведомлений не найдена"

                # Удаляем настройку
                conn.execute("""
                    DELETE FROM notification_settings WHERE id = ?
                """, (setting_id,))

                logger.info(f"Deleted notification setting ID={setting_id}")
                return True, "Настройка уведомлений успешно удалена"

        except Exception as e:
            error_msg = f"Error deleting notification setting: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def update_notification_setting(self, setting_id: int, days_before: int = None, 
                                time: str = None, is_active: bool = None) -> Tuple[bool, str]:
        """Update existing notification setting
        
        Returns:
            Tuple[bool, str]: (success, message) where success indicates if operation 
            was successful and message contains status/error information
        """
        try:
            with self.get_connection() as conn:
                # Проверяем существование настройки
                exists = conn.execute("""
                    SELECT COUNT(*) as count FROM notification_settings WHERE id = ?
                """, (setting_id,)).fetchone()['count'] > 0

                if not exists:
                    return False, "Настройка уведомлений не найдена"

                update_parts = []
                params = []

                if days_before is not None:
                    update_parts.append("days_before = ?")
                    params.append(days_before)
                if time is not None:
                    update_parts.append("time = ?")
                    params.append(time)
                if is_active is not None:
                    update_parts.append("is_active = ?")
                    params.append(is_active)

                if not update_parts:
                    return False, "Не указаны параметры для обновления"

                params.append(setting_id)
                query = f"""
                    UPDATE notification_settings 
                    SET {', '.join(update_parts)}
                    WHERE id = ?
                """

                conn.execute(query, params)

                logger.info(f"Successfully updated notification setting ID={setting_id}")
                return True, "Настройка уведомлений успешно обновлена"

        except Exception as e:
            error_msg = f"Error updating notification setting: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def get_notification_setting(self, setting_id: int) -> Optional[Dict]:
        """Get notification setting by ID"""
        try:
            with self.get_connection() as conn:
                result = conn.execute("""
                    SELECT ns.*, nt.name as template_name, nt.template
                    FROM notification_settings ns
                    JOIN notification_templates nt ON ns.template_id = nt.id
                    WHERE ns.id = ?
                """, (setting_id,)).fetchone()

                if result:
                    return dict(result)
                logger.warning(f"Notification setting with ID={setting_id} not found")
                return None

        except Exception as e:
            logger.error(f"Error getting notification setting: {str(e)}")
            return None

    def update_user_admin_status(self, telegram_id: int, is_admin: bool) -> bool:
        """Update user's admin status
        
        Args:
            telegram_id: Telegram user ID
            is_admin: New admin status
        
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    UPDATE users 
                    SET is_admin = ?
                    WHERE telegram_id = ?
                """, (is_admin, telegram_id))

                # Check if update was successful
                result = conn.execute("""
                    SELECT changes() as updated_rows
                """).fetchone()

                success = result['updated_rows'] > 0
                logger.info(
                    f"User {telegram_id} admin status updated to {is_admin}. "
                    f"Success: {success}"
                )
                return success

        except Exception as e:
            logger.error(f"Error updating user admin status: {str(e)}")
            return False

    def add_notification_template(self, name: str, template: str, category: str = 'birthday') -> Tuple[bool, Optional[int], str]:
        """Add new notification template
        
        Args:
            name: Template name
            template: Template text
            category: Template category (default: birthday)
        
        Returns:
            Tuple[bool, Optional[int], str]: (success, template_id, message)
        """
        try:
            with self.get_connection() as conn:
                # Check if template with this name already exists
                existing = conn.execute("""
                    SELECT id FROM notification_templates 
                    WHERE name = ? AND category = ?
                """, (name, category)).fetchone()

                if existing:
                    return False, None, "Шаблон с таким именем уже существует"

                cursor = conn.execute("""
                    INSERT INTO notification_templates (name, template, category)
                    VALUES (?, ?, ?)
                """, (name, template, category))

                template_id = cursor.lastrowid
                logger.info(f"Added notification template: {name}, id={template_id}")
                return True, template_id, "Шаблон успешно добавлен"

        except Exception as e:
            error_msg = f"Error adding notification template: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg

    def update_notification_template(self, template_id: int, name: str = None, 
                                template: str = None, category: str = None) -> Tuple[bool, str]:
        """Update existing notification template

        Args:
            template_id: Template ID to update
            name: New template name (optional)
            template: New template text (optional)
            category: New template category (optional)

        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            with self.get_connection() as conn:
                # Check if template exists
                exists = conn.execute("""
                    SELECT COUNT(*) as count FROM notification_templates 
                    WHERE id = ?
                """, (template_id,)).fetchone()['count'] > 0

                if not exists:
                    return False, "Шаблон не найден"

                # Build update query
                update_parts = []
                params = []

                if name is not None:
                    update_parts.append("name = ?")
                    params.append(name)
                if template is not None:
                    update_parts.append("template = ?")
                    params.append(template)
                if category is not None:
                    update_parts.append("category = ?")
                    params.append(category)

                # Always update the updated_at timestamp
                update_parts.append("updated_at = CURRENT_TIMESTAMP")

                if not update_parts:
                    return False, "Не указаны параметры для обновления"

                params.append(template_id)
                query = f"""
                    UPDATE notification_templates 
                    SET {', '.join(update_parts)}
                    WHERE id = ?
                """

                result = conn.execute(query, params)

                if result.rowcount > 0:
                    logger.info(f"Updated notification template ID={template_id}")
                    return True, "Шаблон успешно обновлен"
                return False, "Не удалось обновить шаблон"

        except Exception as e:
            error_msg = f"Error updating notification template: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def delete_notification_template(self, template_id: int) -> Tuple[bool, str]:
        """Delete notification template by ID

        Args:
            template_id: Template ID to delete

        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            with self.get_connection() as conn:
                # Check if template exists and is not in use
                template = conn.execute("""
                    SELECT COUNT(*) as count 
                    FROM notification_settings 
                    WHERE template_id = ? AND is_active = 1
                """, (template_id,)).fetchone()

                if template['count'] > 0:
                    return False, "Шаблон используется в активных настройках уведомлений"

                # Delete the template
                result = conn.execute("""
                    DELETE FROM notification_templates 
                    WHERE id = ?
                """, (template_id,))

                if result.rowcount > 0:
                    # Also delete any inactive settings using this template
                    conn.execute("""
                        DELETE FROM notification_settings 
                        WHERE template_id = ?
                    """, (template_id,))

                    logger.info(f"Deleted notification template ID={template_id}")
                    return True, "✅ Шаблон успешно удален"
                return False, "❌ Шаблон не найден"

        except Exception as e:
            error_msg = f"Error deleting notification template: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def update_template_status(self, template_id: int, is_active: bool) -> Tuple[bool, str]:
        """Update template active status
        
        Args:
            template_id: Template ID to update
            is_active: New active status
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            with self.get_connection() as conn:
                result = conn.execute("""
                    UPDATE notification_templates 
                    SET is_active = ?
                    WHERE id = ?
                """, (is_active, template_id))

                if result.rowcount > 0:
                    status = "активирован" if is_active else "деактивирован"
                    logger.info(f"Template ID={template_id} {status}")
                    return True, f"Шаблон успешно {status}"
                return False, "Шаблон не найден"

        except Exception as e:
            error_msg = f"Error updating template status: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def get_templates(self, category: str = None) -> List[Dict]:
        """Get all notification templates, optionally filtered by category

        Args:
            category: Optional category filter

        Returns:
            List[Dict]: List of templates with their settings
        """
        try:
            with self.get_connection() as conn:
                query = """
                    SELECT t.*, 
                           datetime(t.created_at, 'localtime') as created_at,
                           datetime(t.updated_at, 'localtime') as updated_at,
                           json_group_array(
                               CASE 
                                   WHEN s.id IS NOT NULL THEN json_object(
                                       'id', s.id,
                                       'days_before', s.days_before,
                                       'time', s.time,
                                       'is_active', s.is_active
                                   )
                                   ELSE NULL
                               END
                           ) as settings
                    FROM notification_templates t
                    LEFT JOIN notification_settings s ON s.template_id = t.id
                """

                params = []
                if category:
                    query += " WHERE t.category = ?"
                    params.append(category)

                query += " GROUP BY t.id ORDER BY t.created_at DESC"

                results = conn.execute(query, params).fetchall()
                templates = []

                for row in results:
                    template = dict(row)
                    # Parse settings JSON and filter out NULL values
                    settings = json.loads(template['settings'])
                    template['settings'] = [s for s in settings if s is not None]
                    templates.append(template)

                logger.info(f"Retrieved {len(templates)} templates" + 
                         (f" for category '{category}'" if category else ""))
                return templates

        except Exception as e:
            logger.error(f"Error getting templates: {str(e)}")
            return []

    def check_table_structure(self):
        """Check database table structure and log details"""
        try:
            with self.get_connection() as conn:
                # Get table info
                table_info = conn.execute("PRAGMA table_info(users)").fetchall()
                logger.info("Current users table structure:")
                for column in table_info:
                    logger.info(f"Column: {column['name']}, Type: {column['type']}")
                return True
        except Exception as e:
            logger.error(f"Error checking table structure: {str(e)}")
            return False