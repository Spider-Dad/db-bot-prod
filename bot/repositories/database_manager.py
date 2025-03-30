"""
Менеджер базы данных.

Этот модуль содержит класс DatabaseManager, отвечающий за инициализацию базы данных,
проверку её структуры и создание базового подключения.
"""

import sqlite3
import logging
import os
import shutil
from contextlib import contextmanager
from typing import Optional, List
import json
from datetime import datetime

from config import DB_PATH, SCHEMA_PATH
from bot.constants import DEFAULT_NOTIFICATION_SETTINGS, DEFAULT_NOTIFICATION_TEMPLATES
from bot.core.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Менеджер базы данных.
    
    Отвечает за инициализацию базы данных, проверку её структуры
    и создание базового подключения.
    """
    
    def __init__(self, db_path: str = DB_PATH):
        """
        Инициализация менеджера базы данных.
        
        Args:
            db_path: Путь к файлу базы данных SQLite
        """
        self.db_path = db_path
        self.backup_dir = os.path.join(os.path.dirname(self.db_path), "backups")
        self._ensure_data_directory()
        self._init_db()
        
    def _ensure_data_directory(self):
        """
        Создание директорий для данных и резервных копий.
        
        Создает директории для базы данных и резервных копий, если они не существуют.
        """
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
        """
        Контекстный менеджер для соединения с базой данных.
        
        Автоматически открывает и закрывает соединение с базой данных,
        а также управляет транзакциями (commit/rollback).
        
        Yields:
            Соединение с базой данных
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка базы данных: {str(e)}")
            raise
        finally:
            conn.close()
            
    def _init_db(self):
        """
        Инициализация базы данных.
        
        Создает базу данных и таблицы, если они не существуют,
        а также инициализирует настройки по умолчанию.
        """
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
        """
        Инициализация настроек по умолчанию.
        
        Создает таблицы для шаблонов и настроек уведомлений, если они не существуют,
        а также добавляет шаблоны и настройки по умолчанию.
        """
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
            logger.error(f"Ошибка при инициализации настроек по умолчанию: {str(e)}")
            raise
            
    def check_table_structure(self):
        """
        Проверка структуры таблиц.
        
        Проверяет структуру таблиц и создает отсутствующие таблицы и столбцы.
        """
        try:
            with self.get_connection() as conn:
                # Проверяем существование базовых таблиц
                tables = {
                    "users": [
                        "id INTEGER PRIMARY KEY AUTOINCREMENT",
                        "telegram_id INTEGER UNIQUE NOT NULL",
                        "username TEXT",
                        "first_name TEXT NOT NULL",
                        "last_name TEXT",
                        "birth_date TEXT NOT NULL",
                        "is_admin BOOLEAN DEFAULT 0",
                        "is_subscribed BOOLEAN DEFAULT 0",
                        "is_notifications_enabled BOOLEAN DEFAULT 1",
                        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                        "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                    ],
                    "notification_templates": [
                        "id INTEGER PRIMARY KEY AUTOINCREMENT",
                        "name TEXT NOT NULL",
                        "template TEXT NOT NULL",
                        "category TEXT NOT NULL",
                        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                        "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                        "is_active BOOLEAN DEFAULT 1"
                    ],
                    "notification_settings": [
                        "id INTEGER PRIMARY KEY AUTOINCREMENT",
                        "template_id INTEGER NOT NULL",
                        "days_before INTEGER NOT NULL",
                        "time TEXT NOT NULL",
                        "is_active BOOLEAN DEFAULT 1",
                        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                        "FOREIGN KEY (template_id) REFERENCES notification_templates(id)"
                    ],
                    "notification_logs": [
                        "id INTEGER PRIMARY KEY AUTOINCREMENT",
                        "user_id INTEGER NOT NULL",
                        "message TEXT NOT NULL",
                        "status TEXT NOT NULL",
                        "error_message TEXT",
                        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                        "FOREIGN KEY (user_id) REFERENCES users(id)"
                    ]
                }
                
                for table_name, columns in tables.items():
                    # Проверяем существование таблицы
                    table_exists = conn.execute(f"""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name='{table_name}'
                    """).fetchone()
                    
                    if not table_exists:
                        # Создаем таблицу
                        logger.info(f"Создание таблицы {table_name}")
                        conn.execute(f"""
                            CREATE TABLE {table_name} (
                                {', '.join(columns)}
                            )
                        """)
                    else:
                        # Проверяем структуру таблицы
                        existing_columns = [row['name'] for row in conn.execute(f"PRAGMA table_info({table_name})")]
                        
                        for column in columns:
                            column_name = column.split()[0]
                            if column_name not in existing_columns:
                                # Добавляем отсутствующий столбец
                                logger.info(f"Добавление столбца {column_name} в таблицу {table_name}")
                                conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column}")
                
                logger.info("Структура таблиц проверена и обновлена")
                
        except Exception as e:
            logger.error(f"Ошибка проверки структуры таблиц: {str(e)}")
            raise
    
    def create_backup(self) -> Optional[str]:
        """
        Создание резервной копии базы данных.
        
        Returns:
            Optional[str]: Путь к файлу резервной копии или None в случае ошибки
        """
        try:
            # Проверяем существование базы данных
            if not os.path.exists(self.db_path):
                logger.error(f"База данных не найдена: {self.db_path}")
                return None
                
            # Создаем имя файла резервной копии
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{timestamp}.db"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # Копируем файл базы данных
            shutil.copy2(self.db_path, backup_path)
            
            logger.info(f"Резервная копия создана: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Ошибка создания резервной копии: {str(e)}")
            return None
            
    def list_backups(self) -> List[str]:
        """
        Получение списка путей к файлам резервных копий.
        
        Returns:
            List[str]: Список путей к файлам резервных копий
        """
        try:
            backups = [f for f in os.listdir(self.backup_dir) if f.startswith("backup_") and f.endswith(".db")]
            backups.sort(reverse=True)  # Сортируем по убыванию (новые в начале)
            return [os.path.join(self.backup_dir, b) for b in backups]
        except Exception as e:
            logger.error(f"Ошибка получения списка резервных копий: {str(e)}")
            return []
    
    def get_backup_list(self) -> List[dict]:
        """
        Получение списка резервных копий с информацией о них.
        
        Returns:
            List[dict]: Список словарей с информацией о резервных копиях
        """
        try:
            # Получаем список файлов резервных копий
            backup_files = []
            
            # Смотрим все .db файлы в директории резервных копий
            for f in os.listdir(self.backup_dir):
                if f.endswith(".db") and (f != "birthday_bot.db"):  # Исключаем основной файл БД
                    try:
                        file_path = os.path.join(self.backup_dir, f)
                        file_stats = os.stat(file_path)
                        
                        # Получаем дату создания файла из метаданных файловой системы
                        created_at = datetime.fromtimestamp(file_stats.st_ctime)
                        
                        # Получаем размер файла
                        size = file_stats.st_size
                        
                        backup_files.append({
                            'filename': f,
                            'path': file_path,
                            'created_at': created_at,
                            'size': size
                        })
                    except (ValueError, OSError) as e:
                        logger.warning(f"Ошибка при обработке файла резервной копии {f}: {str(e)}")
            
            # Сортируем резервные копии по дате создания (новые в начале)
            backup_files.sort(key=lambda x: x['created_at'], reverse=True)
            return backup_files
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о резервных копиях: {str(e)}")
            return []
    
    def get_backup_path(self, backup_name: str) -> Optional[str]:
        """
        Получение полного пути к файлу резервной копии.
        
        Args:
            backup_name: Имя файла резервной копии
            
        Returns:
            str: Полный путь к файлу резервной копии или None, если файл не найден
        """
        try:
            # Формируем полный путь
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            # Проверяем существование файла
            if not os.path.exists(backup_path) or not os.path.isfile(backup_path):
                logger.warning(f"Файл резервной копии не найден: {backup_path}")
                return None
                
            return backup_path
            
        except Exception as e:
            logger.error(f"Ошибка получения пути к резервной копии: {str(e)}")
            return None
    
    def backup_exists(self, backup_name: str) -> bool:
        """
        Проверка существования файла резервной копии.
        
        Args:
            backup_name: Имя файла резервной копии
            
        Returns:
            bool: True, если файл существует, иначе False
        """
        try:
            backup_path = os.path.join(self.backup_dir, backup_name)
            return os.path.exists(backup_path) and os.path.isfile(backup_path)
        except Exception as e:
            logger.error(f"Ошибка проверки существования резервной копии: {str(e)}")
            return False
    
    def delete_backup(self, backup_name: str) -> bool:
        """
        Удаление файла резервной копии.
        
        Args:
            backup_name: Имя файла резервной копии
            
        Returns:
            bool: True, если файл успешно удален, иначе False
        """
        try:
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            # Проверяем существование файла
            if not os.path.exists(backup_path) or not os.path.isfile(backup_path):
                logger.warning(f"Файл резервной копии не найден: {backup_path}")
                return False
                
            # Удаляем файл
            os.remove(backup_path)
            logger.info(f"Файл резервной копии удален: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка удаления резервной копии: {str(e)}")
            return False
            
    def backup_database(self, comment: str = None) -> Optional[str]:
        """
        Создание резервной копии базы данных.
        
        Args:
            comment: Комментарий к резервной копии (не используется в текущей реализации)
            
        Returns:
            str: Полный путь к файлу резервной копии или None в случае ошибки
        """
        return self.create_backup()
        
    def save_uploaded_backup(self, file_content: bytes, filename: str) -> Optional[str]:
        """
        Сохранение загруженной резервной копии.
        
        Args:
            file_content: Содержимое файла резервной копии
            filename: Имя файла резервной копии
            
        Returns:
            str: Полный путь к сохраненному файлу или None в случае ошибки
        """
        try:
            # Формируем путь для сохранения файла
            backup_path = os.path.join(self.backup_dir, filename)
            
            # Сохраняем файл
            with open(backup_path, 'wb') as f:
                f.write(file_content)
                
            logger.info(f"Загруженная резервная копия сохранена: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Ошибка сохранения загруженной резервной копии: {str(e)}")
            return None
            
    def restore_from_backup(self, backup_path: str) -> bool:
        """
        Восстановление базы данных из резервной копии.
        
        Args:
            backup_path: Путь к файлу резервной копии
            
        Returns:
            bool: True, если восстановление прошло успешно, иначе False
        """
        try:
            # Проверяем существование файла резервной копии
            if not os.path.exists(backup_path):
                logger.error(f"Файл резервной копии не найден: {backup_path}")
                return False
                
            # Создаем резервную копию текущей базы данных
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            current_backup_filename = f"before_restore_{timestamp}.db"
            current_backup_path = os.path.join(self.backup_dir, current_backup_filename)
            
            # Копируем текущую базу данных
            if os.path.exists(self.db_path):
                shutil.copy2(self.db_path, current_backup_path)
                
            # Восстанавливаем из резервной копии
            shutil.copy2(backup_path, self.db_path)
            
            logger.info(f"База данных восстановлена из резервной копии: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка восстановления из резервной копии: {str(e)}")
            return False 