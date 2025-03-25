"""
Репозиторий пользователей.

Этот модуль содержит класс UserRepository, отвечающий за управление
пользователями в базе данных.
"""

from typing import List, Dict, Optional, Any, Tuple
import logging
from datetime import datetime, timedelta, date
import sqlite3

from bot.core.models import User
from bot.core.base_repository import BaseRepository
from bot.repositories.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository):
    """
    Репозиторий для работы с пользователями.
    
    Предоставляет методы для добавления, обновления, удаления и получения информации
    о пользователях из базы данных.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Инициализация репозитория пользователей.
        
        Args:
            db_manager: Менеджер базы данных
        """
        super().__init__(db_manager)
        
    def add_user(self, user: User) -> Optional[int]:
        """
        Добавление нового пользователя в базу данных.
        
        Args:
            user: Объект пользователя для добавления
            
        Returns:
            Optional[int]: ID добавленного пользователя или None в случае ошибки
        """
        try:
            with self._db_manager.get_connection() as conn:
                # Проверяем, существует ли таблица
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
                
                # Проверяем, существует ли пользователь с таким telegram_id
                existing_user = conn.execute(
                    "SELECT id FROM users WHERE telegram_id = ?",
                    (user.telegram_id,)
                ).fetchone()
                
                if existing_user:
                    # Обновляем существующего пользователя
                    conn.execute("""
                    UPDATE users
                    SET 
                        username = ?,
                        first_name = ?,
                        last_name = ?,
                        birth_date = ?,
                        is_admin = ?,
                        is_subscribed = ?,
                        is_notifications_enabled = ?
                    WHERE telegram_id = ?
                    """, (
                        user.username,
                        user.first_name,
                        user.last_name,
                        user.birth_date,
                        user.is_admin,
                        user.is_subscribed,
                        user.is_notifications_enabled,
                        user.telegram_id
                    ))
                    
                    logger.info(f"Пользователь обновлен: {user.first_name} {user.last_name} (ID: {user.telegram_id})")
                    return existing_user['id']
                else:
                    # Добавляем нового пользователя
                    cursor = conn.execute("""
                    INSERT INTO users (
                        telegram_id,
                        username,
                        first_name,
                        last_name,
                        birth_date,
                        is_admin,
                        is_subscribed,
                        is_notifications_enabled
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        user.telegram_id,
                        user.username,
                        user.first_name,
                        user.last_name,
                        user.birth_date,
                        user.is_admin,
                        user.is_subscribed,
                        user.is_notifications_enabled
                    ))
                    
                    logger.info(f"Новый пользователь добавлен: {user.first_name} {user.last_name} (ID: {user.telegram_id})")
                    return cursor.lastrowid
                    
        except Exception as e:
            logger.error(f"Ошибка добавления пользователя: {str(e)}")
            return None
            
    def delete_user(self, telegram_id: int) -> bool:
        """
        Удаление пользователя из базы данных.
        
        Args:
            telegram_id: Telegram ID пользователя для удаления
            
        Returns:
            bool: True, если пользователь удален успешно, иначе False
        """
        try:
            with self._db_manager.get_connection() as conn:
                # Проверяем, существует ли пользователь
                existing_user = conn.execute(
                    "SELECT id FROM users WHERE telegram_id = ?",
                    (telegram_id,)
                ).fetchone()
                
                if not existing_user:
                    logger.warning(f"Пользователь с ID {telegram_id} не найден для удаления")
                    return False
                    
                # Удаляем пользователя
                conn.execute("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))
                logger.info(f"Пользователь удален: ID {telegram_id}")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка удаления пользователя: {str(e)}")
            return False
            
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        Получение пользователя по его Telegram ID.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            Optional[User]: Объект пользователя или None, если пользователь не найден
        """
        try:
            with self._db_manager.get_connection() as conn:
                user_data = conn.execute("""
                SELECT 
                    id,
                    telegram_id,
                    username,
                    first_name,
                    last_name,
                    birth_date,
                    is_admin,
                    is_subscribed,
                    is_notifications_enabled,
                    created_at
                FROM users
                WHERE telegram_id = ?
                """, (telegram_id,)).fetchone()
                
                if not user_data:
                    return None
                    
                return User(
                    id=user_data['id'],
                    telegram_id=user_data['telegram_id'],
                    username=user_data['username'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    birth_date=user_data['birth_date'],
                    is_admin=bool(user_data['is_admin']),
                    is_subscribed=bool(user_data['is_subscribed']),
                    is_notifications_enabled=bool(user_data['is_notifications_enabled']),
                    created_at=user_data['created_at'],
                    updated_at=user_data['created_at']  # Используем created_at вместо updated_at
                )
                
        except Exception as e:
            logger.error(f"Ошибка получения пользователя: {str(e)}")
            return None
            
    def get_all_users(self) -> List[User]:
        """
        Получение всех пользователей из базы данных.
        
        Returns:
            List[User]: Список объектов пользователей
        """
        try:
            with self._db_manager.get_connection() as conn:
                users_data = conn.execute("""
                SELECT 
                    id,
                    telegram_id,
                    username,
                    first_name,
                    last_name,
                    birth_date,
                    is_admin,
                    is_subscribed,
                    is_notifications_enabled,
                    created_at
                FROM users
                """).fetchall()
                
                users = []
                for user_data in users_data:
                    users.append(User(
                        id=user_data['id'],
                        telegram_id=user_data['telegram_id'],
                        username=user_data['username'],
                        first_name=user_data['first_name'],
                        last_name=user_data['last_name'],
                        birth_date=user_data['birth_date'],
                        is_admin=bool(user_data['is_admin']),
                        is_subscribed=bool(user_data['is_subscribed']),
                        is_notifications_enabled=bool(user_data['is_notifications_enabled']),
                        created_at=user_data['created_at'],
                        updated_at=user_data['created_at']  # Используем created_at вместо updated_at
                    ))
                    
                return users
                
        except Exception as e:
            logger.error(f"Ошибка получения всех пользователей: {str(e)}")
            return []
            
    def get_users_with_birthdays_between(self, start_date: date, end_date: date) -> List[User]:
        """
        Получение пользователей, у которых день рождения в указанном диапазоне дат.
        
        Args:
            start_date: Начальная дата диапазона
            end_date: Конечная дата диапазона
            
        Returns:
            List[User]: Список пользователей с днями рождения в указанном диапазоне
        """
        try:
            with self._db_manager.get_connection() as conn:
                # Получаем пользователей, у которых месяц и день рождения попадают в указанный диапазон
                users_data = conn.execute("""
                SELECT 
                    id,
                    telegram_id,
                    username,
                    first_name,
                    last_name,
                    birth_date,
                    is_admin,
                    is_subscribed,
                    is_notifications_enabled,
                    created_at
                FROM users
                WHERE 
                    is_notifications_enabled = 1
                    AND is_subscribed = 1
                """).fetchall()
                
                # Фильтруем пользователей по дате рождения
                users = []
                for user_data in users_data:
                    try:
                        birth_date_str = user_data['birth_date']
                        birth_date_obj = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
                        
                        # Создаем "эквивалентную" дату рождения для текущего года
                        current_year = datetime.now().year
                        current_year_birthday = date(current_year, birth_date_obj.month, birth_date_obj.day)
                        
                        # Проверяем, попадает ли день рождения в указанный диапазон
                        if start_date <= current_year_birthday <= end_date:
                            users.append(User(
                                id=user_data['id'],
                                telegram_id=user_data['telegram_id'],
                                username=user_data['username'],
                                first_name=user_data['first_name'],
                                last_name=user_data['last_name'],
                                birth_date=user_data['birth_date'],
                                is_admin=bool(user_data['is_admin']),
                                is_subscribed=bool(user_data['is_subscribed']),
                                is_notifications_enabled=bool(user_data['is_notifications_enabled']),
                                created_at=user_data['created_at'],
                                updated_at=user_data['created_at']  # Используем created_at вместо updated_at
                            ))
                    except ValueError as ve:
                        logger.warning(f"Неверный формат даты рождения для пользователя {user_data['id']}: {str(ve)}")
                    
                return users
                
        except Exception as e:
            logger.error(f"Ошибка получения пользователей по диапазону дат: {str(e)}")
            return []
            
    def get_upcoming_birthdays(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """
        Получение ближайших дней рождения пользователей.
        
        Args:
            days_ahead: Количество дней вперед для поиска
            
        Returns:
            List[Dict[str, Any]]: Список словарей с информацией о пользователях и их днях рождения
        """
        try:
            today = datetime.now().date()
            end_date = today + timedelta(days=days_ahead)
            
            users = self.get_users_with_birthdays_between(today, end_date)
            
            # Преобразуем в список словарей с дополнительной информацией
            birthday_info = []
            current_year = datetime.now().year
            
            for user in users:
                try:
                    birth_date_obj = datetime.strptime(user.birth_date, "%Y-%m-%d").date()
                    current_year_birthday = date(current_year, birth_date_obj.month, birth_date_obj.day)
                    
                    # Рассчитываем количество дней до дня рождения
                    days_until = (current_year_birthday - today).days
                    
                    # Рассчитываем возраст
                    age = current_year - birth_date_obj.year
                    
                    birthday_info.append({
                        "user": user,
                        "days_until": days_until,
                        "birthday_date": current_year_birthday,
                        "age": age
                    })
                except ValueError as ve:
                    logger.warning(f"Неверный формат даты рождения для пользователя {user.id}: {str(ve)}")
            
            # Сортируем по количеству дней до дня рождения
            birthday_info.sort(key=lambda x: x["days_until"])
            
            return birthday_info
                
        except Exception as e:
            logger.error(f"Ошибка получения ближайших дней рождения: {str(e)}")
            return []
            
    def update_user(self, user: User) -> bool:
        """
        Обновление информации о пользователе.
        
        Args:
            user: Объект пользователя с обновленными данными
            
        Returns:
            bool: True, если обновление прошло успешно, иначе False
        """
        try:
            with self._db_manager.get_connection() as conn:
                # Проверяем, существует ли пользователь
                existing_user = conn.execute(
                    "SELECT id FROM users WHERE telegram_id = ?",
                    (user.telegram_id,)
                ).fetchone()
                
                if not existing_user:
                    logger.warning(f"Пользователь с ID {user.telegram_id} не найден для обновления")
                    return False
                    
                # Обновляем пользователя
                conn.execute("""
                UPDATE users
                SET 
                    username = ?,
                    first_name = ?,
                    last_name = ?,
                    birth_date = ?,
                    is_admin = ?,
                    is_subscribed = ?,
                    is_notifications_enabled = ?
                WHERE telegram_id = ?
                """, (
                    user.username,
                    user.first_name,
                    user.last_name,
                    user.birth_date,
                    user.is_admin,
                    user.is_subscribed,
                    user.is_notifications_enabled,
                    user.telegram_id
                ))
                
                logger.info(f"Пользователь обновлен: {user.first_name} {user.last_name} (ID: {user.telegram_id})")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка обновления пользователя: {str(e)}")
            return False
            
    def update_user_subscription(self, telegram_id: int, is_subscribed: bool) -> bool:
        """
        Обновление статуса подписки пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
            is_subscribed: Новый статус подписки
            
        Returns:
            bool: True, если обновление прошло успешно, иначе False
        """
        try:
            with self._db_manager.get_connection() as conn:
                # Проверяем, существует ли пользователь
                existing_user = conn.execute(
                    "SELECT id FROM users WHERE telegram_id = ?",
                    (telegram_id,)
                ).fetchone()
                
                if not existing_user:
                    logger.warning(f"Пользователь с ID {telegram_id} не найден для обновления подписки")
                    return False
                    
                # Обновляем статус подписки
                conn.execute("""
                UPDATE users
                SET 
                    is_subscribed = ?
                WHERE telegram_id = ?
                """, (is_subscribed, telegram_id))
                
                logger.info(f"Статус подписки пользователя обновлен: ID {telegram_id}, is_subscribed={is_subscribed}")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка обновления статуса подписки пользователя: {str(e)}")
            return False
            
    def update_user_notifications(self, telegram_id: int, is_notifications_enabled: bool) -> bool:
        """
        Обновление статуса уведомлений пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
            is_notifications_enabled: Новый статус уведомлений
            
        Returns:
            bool: True, если обновление прошло успешно, иначе False
        """
        try:
            with self._db_manager.get_connection() as conn:
                # Проверяем, существует ли пользователь
                existing_user = conn.execute(
                    "SELECT id FROM users WHERE telegram_id = ?",
                    (telegram_id,)
                ).fetchone()
                
                if not existing_user:
                    logger.warning(f"Пользователь с ID {telegram_id} не найден для обновления настроек уведомлений")
                    return False
                    
                # Обновляем статус уведомлений
                conn.execute("""
                UPDATE users
                SET 
                    is_notifications_enabled = ?
                WHERE telegram_id = ?
                """, (is_notifications_enabled, telegram_id))
                
                logger.info(f"Статус уведомлений пользователя обновлен: ID {telegram_id}, is_notifications_enabled={is_notifications_enabled}")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка обновления статуса уведомлений пользователя: {str(e)}")
            return False
            
    def promote_to_admin(self, telegram_id: int) -> bool:
        """
        Назначение пользователя администратором.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            bool: True, если обновление прошло успешно, иначе False
        """
        try:
            with self._db_manager.get_connection() as conn:
                # Проверяем, существует ли пользователь
                existing_user = conn.execute(
                    "SELECT id FROM users WHERE telegram_id = ?",
                    (telegram_id,)
                ).fetchone()
                
                if not existing_user:
                    logger.warning(f"Пользователь с ID {telegram_id} не найден для назначения администратором")
                    return False
                    
                # Назначаем пользователя администратором
                conn.execute("""
                UPDATE users
                SET 
                    is_admin = 1
                WHERE telegram_id = ?
                """, (telegram_id,))
                
                logger.info(f"Пользователь с ID {telegram_id} назначен администратором")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка назначения пользователя администратором: {str(e)}")
            return False
            
    def demote_from_admin(self, telegram_id: int) -> bool:
        """
        Отзыв прав администратора у пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            bool: True, если обновление прошло успешно, иначе False
        """
        try:
            with self._db_manager.get_connection() as conn:
                # Проверяем, существует ли пользователь
                existing_user = conn.execute(
                    "SELECT id FROM users WHERE telegram_id = ?",
                    (telegram_id,)
                ).fetchone()
                
                if not existing_user:
                    logger.warning(f"Пользователь с ID {telegram_id} не найден для отзыва прав администратора")
                    return False
                    
                # Отзываем права администратора
                conn.execute("""
                UPDATE users
                SET 
                    is_admin = 0
                WHERE telegram_id = ?
                """, (telegram_id,))
                
                logger.info(f"У пользователя с ID {telegram_id} отозваны права администратора")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка отзыва прав администратора у пользователя: {str(e)}")
            return False

    # Реализация абстрактных методов из BaseRepository
    
    def to_entity(self, data: Dict[str, Any]) -> User:
        """
        Преобразование данных из базы данных в объект User.
        
        Args:
            data: Данные из базы данных
            
        Returns:
            User: Объект пользователя
        """
        return User(
            id=data.get('id'),
            telegram_id=data.get('telegram_id'),
            username=data.get('username'),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            birth_date=data.get('birth_date'),
            is_admin=bool(data.get('is_admin')),
            is_subscribed=bool(data.get('is_subscribed')),
            is_notifications_enabled=bool(data.get('is_notifications_enabled')),
            created_at=data.get('created_at'),
            updated_at=data.get('created_at')  # Используем created_at вместо updated_at
        )
    
    def to_db_dict(self, entity: User) -> Dict[str, Any]:
        """
        Преобразование объекта User в словарь для сохранения в базе данных.
        
        Args:
            entity: Объект пользователя
            
        Returns:
            Dict[str, Any]: Словарь для сохранения в базе данных
        """
        return {
            'telegram_id': entity.telegram_id,
            'username': entity.username,
            'first_name': entity.first_name,
            'last_name': entity.last_name,
            'birth_date': entity.birth_date,
            'is_admin': entity.is_admin,
            'is_subscribed': entity.is_subscribed,
            'is_notifications_enabled': entity.is_notifications_enabled
        }
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Получение пользователя по ID в базе данных (алиас для get_user_by_id).
        
        Args:
            user_id: ID пользователя в базе данных
            
        Returns:
            Optional[User]: Объект пользователя или None, если пользователь не найден
        """
        return self.get_user_by_id(user_id)
    
    def get_all(self) -> List[User]:
        """
        Получение всех пользователей (алиас для get_all_users).
        
        Returns:
            List[User]: Список всех пользователей
        """
        return self.get_all_users()
    
    def create(self, entity: User) -> int:
        """
        Создание нового пользователя.
        
        Args:
            entity: Объект пользователя
            
        Returns:
            int: ID созданного пользователя или None в случае ошибки
        """
        return self.add_user(entity)
    
    def update(self, id: int, entity: User) -> bool:
        """
        Обновление пользователя.
        
        Args:
            id: ID пользователя
            entity: Объект пользователя
            
        Returns:
            bool: True, если обновление прошло успешно, иначе False
        """
        return self.update_user(entity)
    
    def delete(self, id: int) -> bool:
        """
        Удаление пользователя.
        
        Args:
            id: ID пользователя
            
        Returns:
            bool: True, если удаление прошло успешно, иначе False
        """
        try:
            with self._db_manager.get_connection() as conn:
                user_data = conn.execute("SELECT telegram_id FROM users WHERE id = ?", (id,)).fetchone()
                if not user_data:
                    return False
                
                telegram_id = user_data['telegram_id']
                return self.delete_user(telegram_id)
        except Exception as e:
            logger.error(f"Ошибка удаления пользователя по ID: {str(e)}")
            return False

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Получение пользователя по его ID в базе данных.
        
        Args:
            user_id: ID пользователя в базе данных
            
        Returns:
            Optional[User]: Объект пользователя или None, если пользователь не найден
        """
        try:
            with self._db_manager.get_connection() as conn:
                user_data = conn.execute("""
                SELECT 
                    id,
                    telegram_id,
                    username,
                    first_name,
                    last_name,
                    birth_date,
                    is_admin,
                    is_subscribed,
                    is_notifications_enabled,
                    created_at
                FROM users
                WHERE id = ?
                """, (user_id,)).fetchone()
                
                if not user_data:
                    return None
                    
                return User(
                    id=user_data['id'],
                    telegram_id=user_data['telegram_id'],
                    username=user_data['username'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    birth_date=user_data['birth_date'],
                    is_admin=bool(user_data['is_admin']),
                    is_subscribed=bool(user_data['is_subscribed']),
                    is_notifications_enabled=bool(user_data['is_notifications_enabled']),
                    created_at=user_data['created_at'],
                    updated_at=user_data['created_at']  # Используем created_at вместо updated_at
                )
                
        except Exception as e:
            logger.error(f"Ошибка получения пользователя по ID: {str(e)}")
            return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Получение пользователя по его имени пользователя (username).
        
        Args:
            username: Имя пользователя
            
        Returns:
            Optional[User]: Объект пользователя или None, если пользователь не найден
        """
        try:
            with self._db_manager.get_connection() as conn:
                user_data = conn.execute("""
                SELECT 
                    id,
                    telegram_id,
                    username,
                    first_name,
                    last_name,
                    birth_date,
                    is_admin,
                    is_subscribed,
                    is_notifications_enabled,
                    created_at
                FROM users
                WHERE username = ?
                """, (username,)).fetchone()
                
                if not user_data:
                    return None
                    
                return User(
                    id=user_data['id'],
                    telegram_id=user_data['telegram_id'],
                    username=user_data['username'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    birth_date=user_data['birth_date'],
                    is_admin=bool(user_data['is_admin']),
                    is_subscribed=bool(user_data['is_subscribed']),
                    is_notifications_enabled=bool(user_data['is_notifications_enabled']),
                    created_at=user_data['created_at'],
                    updated_at=user_data['created_at']  # Используем created_at вместо updated_at
                )
                
        except Exception as e:
            logger.error(f"Ошибка получения пользователя по имени пользователя: {str(e)}")
            return None 