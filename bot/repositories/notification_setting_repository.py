"""
Репозиторий настроек уведомлений.

Этот модуль содержит класс NotificationSettingRepository, отвечающий за управление
настройками уведомлений в базе данных.
"""

from typing import List, Dict, Optional, Any, Tuple
import logging
import sqlite3
from datetime import datetime

from bot.core.models import NotificationSetting, NotificationTemplate
from bot.core.base_repository import BaseRepository
from bot.repositories.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class NotificationSettingRepository(BaseRepository):
    """
    Репозиторий для работы с настройками уведомлений.
    
    Предоставляет методы для добавления, обновления, удаления и получения информации
    о настройках уведомлений из базы данных.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Инициализация репозитория настроек уведомлений.
        
        Args:
            db_manager: Менеджер базы данных
        """
        super().__init__(db_manager)
        
    def add_setting(self, setting: NotificationSetting) -> Optional[int]:
        """
        Добавление новой настройки уведомления в базу данных.
        
        Args:
            setting: Объект настройки уведомления для добавления
            
        Returns:
            Optional[int]: ID добавленной настройки или None в случае ошибки
        """
        try:
            with self._db_manager.get_connection() as conn:
                # Проверяем, существует ли таблица
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
                
                # Проверяем, существует ли настройка с такими параметрами
                existing_setting = conn.execute("""
                    SELECT id FROM notification_settings 
                    WHERE template_id = ? AND days_before = ? AND time = ?
                """, (setting.template_id, setting.days_before, setting.time)).fetchone()
                
                if existing_setting:
                    # Обновляем существующую настройку
                    conn.execute("""
                    UPDATE notification_settings
                    SET 
                        is_active = ?
                    WHERE id = ?
                    """, (
                        setting.is_active,
                        existing_setting['id']
                    ))
                    
                    logger.info(f"Настройка обновлена: template_id={setting.template_id}, days_before={setting.days_before}, time={setting.time}")
                    return existing_setting['id']
                else:
                    # Добавляем новую настройку
                    cursor = conn.execute("""
                    INSERT INTO notification_settings (
                        template_id,
                        days_before,
                        time,
                        is_active
                    ) VALUES (?, ?, ?, ?)
                    """, (
                        setting.template_id,
                        setting.days_before,
                        setting.time,
                        setting.is_active
                    ))
                    
                    logger.info(f"Новая настройка добавлена: template_id={setting.template_id}, days_before={setting.days_before}, time={setting.time}")
                    return cursor.lastrowid
                    
        except Exception as e:
            logger.error(f"Ошибка добавления настройки: {str(e)}")
            return None
            
    def delete_setting(self, setting_id: int) -> bool:
        """
        Удаление настройки уведомления из базы данных.
        
        Args:
            setting_id: ID настройки для удаления
            
        Returns:
            bool: True, если настройка удалена успешно, иначе False
        """
        try:
            with self._db_manager.get_connection() as conn:
                # Проверяем, существует ли настройка
                existing_setting = conn.execute(
                    "SELECT id FROM notification_settings WHERE id = ?",
                    (setting_id,)
                ).fetchone()
                
                if not existing_setting:
                    logger.warning(f"Настройка с ID {setting_id} не найдена для удаления")
                    return False
                    
                # Удаляем настройку
                conn.execute("DELETE FROM notification_settings WHERE id = ?", (setting_id,))
                logger.info(f"Настройка удалена: ID {setting_id}")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка удаления настройки: {str(e)}")
            return False
            
    def get_setting_by_id(self, setting_id: int) -> Optional[NotificationSetting]:
        """
        Получение настройки уведомления по её ID.
        
        Args:
            setting_id: ID настройки
            
        Returns:
            Optional[NotificationSetting]: Объект настройки или None, если настройка не найдена
        """
        try:
            with self._db_manager.get_connection() as conn:
                setting_data = conn.execute("""
                SELECT 
                    id,
                    template_id,
                    days_before,
                    time,
                    is_active,
                    created_at
                FROM notification_settings
                WHERE id = ?
                """, (setting_id,)).fetchone()
                
                if not setting_data:
                    return None
                    
                return NotificationSetting(
                    id=setting_data['id'],
                    template_id=setting_data['template_id'],
                    days_before=setting_data['days_before'],
                    time=setting_data['time'],
                    is_active=bool(setting_data['is_active']),
                    created_at=setting_data['created_at']
                )
                
        except Exception as e:
            logger.error(f"Ошибка получения настройки: {str(e)}")
            return None
            
    def get_all_settings(self, active_only: bool = False) -> List[NotificationSetting]:
        """
        Получение всех настроек уведомлений из базы данных.
        
        Args:
            active_only: Если True, возвращает только активные настройки
            
        Returns:
            List[NotificationSetting]: Список объектов настроек
        """
        try:
            with self._db_manager.get_connection() as conn:
                query = """
                SELECT 
                    id,
                    template_id,
                    days_before,
                    time,
                    is_active,
                    created_at
                FROM notification_settings
                """
                
                if active_only:
                    query += " WHERE is_active = 1"
                    
                query += " ORDER BY days_before, time"
                
                settings_data = conn.execute(query).fetchall()
                
                settings = []
                for setting_data in settings_data:
                    settings.append(NotificationSetting(
                        id=setting_data['id'],
                        template_id=setting_data['template_id'],
                        days_before=setting_data['days_before'],
                        time=setting_data['time'],
                        is_active=bool(setting_data['is_active']),
                        created_at=setting_data['created_at']
                    ))
                    
                return settings
                
        except Exception as e:
            logger.error(f"Ошибка получения всех настроек: {str(e)}")
            return []
            
    def get_settings_by_template_id(self, template_id: int, active_only: bool = False) -> List[NotificationSetting]:
        """
        Получение настроек уведомлений по ID шаблона.
        
        Args:
            template_id: ID шаблона
            active_only: Если True, возвращает только активные настройки
            
        Returns:
            List[NotificationSetting]: Список объектов настроек
        """
        try:
            with self._db_manager.get_connection() as conn:
                query = """
                SELECT 
                    id,
                    template_id,
                    days_before,
                    time,
                    is_active,
                    created_at
                FROM notification_settings
                WHERE template_id = ?
                """
                
                params = [template_id]
                
                if active_only:
                    query += " AND is_active = 1"
                    
                query += " ORDER BY days_before, time"
                
                settings_data = conn.execute(query, params).fetchall()
                
                settings = []
                for setting_data in settings_data:
                    settings.append(NotificationSetting(
                        id=setting_data['id'],
                        template_id=setting_data['template_id'],
                        days_before=setting_data['days_before'],
                        time=setting_data['time'],
                        is_active=bool(setting_data['is_active']),
                        created_at=setting_data['created_at']
                    ))
                    
                return settings
                
        except Exception as e:
            logger.error(f"Ошибка получения настроек по ID шаблона: {str(e)}")
            return []
            
    def get_settings_with_templates(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """
        Получение настроек уведомлений вместе с их шаблонами.
        
        Args:
            active_only: Если True, возвращает только активные настройки
            
        Returns:
            List[Dict[str, Any]]: Список словарей, содержащих настройки и шаблоны
        """
        try:
            with self._db_manager.get_connection() as conn:
                query = """
                SELECT 
                    s.id as setting_id,
                    s.template_id,
                    s.days_before,
                    s.time,
                    s.is_active as setting_is_active,
                    s.created_at as setting_created_at,
                    t.id as template_id,
                    t.name as template_name,
                    t.template,
                    t.category,
                    t.is_active as template_is_active,
                    t.created_at as template_created_at,
                    t.updated_at as template_updated_at
                FROM notification_settings s
                JOIN notification_templates t ON s.template_id = t.id
                """
                
                if active_only:
                    query += " WHERE s.is_active = 1 AND t.is_active = 1"
                    
                query += " ORDER BY s.days_before, s.time, t.category, t.name"
                
                results = conn.execute(query).fetchall()
                
                settings_with_templates = []
                for row in results:
                    template = NotificationTemplate(
                        id=row['template_id'],
                        name=row['template_name'],
                        template=row['template'],
                        category=row['category'],
                        is_active=bool(row['template_is_active']),
                        created_at=row['template_created_at'],
                        updated_at=row['template_updated_at']
                    )
                    
                    setting = NotificationSetting(
                        id=row['setting_id'],
                        template_id=row['template_id'],
                        days_before=row['days_before'],
                        time=row['time'],
                        is_active=bool(row['setting_is_active']),
                        created_at=row['setting_created_at']
                    )
                    
                    settings_with_templates.append({
                        'setting': setting,
                        'template': template
                    })
                    
                return settings_with_templates
                
        except Exception as e:
            logger.error(f"Ошибка получения настроек с шаблонами: {str(e)}")
            return []
            
    def update_setting(self, setting: NotificationSetting) -> bool:
        """
        Обновление информации о настройке уведомления.
        
        Args:
            setting: Объект настройки с обновленными данными
            
        Returns:
            bool: True, если обновление прошло успешно, иначе False
        """
        try:
            with self._db_manager.get_connection() as conn:
                # Проверяем, существует ли настройка
                existing_setting = conn.execute(
                    "SELECT id FROM notification_settings WHERE id = ?",
                    (setting.id,)
                ).fetchone()
                
                if not existing_setting:
                    logger.warning(f"Настройка с ID {setting.id} не найдена для обновления")
                    return False
                    
                # Обновляем настройку
                conn.execute("""
                UPDATE notification_settings
                SET 
                    template_id = ?,
                    days_before = ?,
                    time = ?,
                    is_active = ?
                WHERE id = ?
                """, (
                    setting.template_id,
                    setting.days_before,
                    setting.time,
                    setting.is_active,
                    setting.id
                ))
                
                logger.info(f"Настройка обновлена: ID {setting.id}")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка обновления настройки: {str(e)}")
            return False
            
    def toggle_setting_active(self, setting_id: int, is_active: bool) -> bool:
        """
        Изменение статуса активности настройки уведомления.
        
        Args:
            setting_id: ID настройки
            is_active: Новый статус активности
            
        Returns:
            bool: True, если обновление прошло успешно, иначе False
        """
        try:
            with self._db_manager.get_connection() as conn:
                # Проверяем, существует ли настройка
                existing_setting = conn.execute(
                    "SELECT id FROM notification_settings WHERE id = ?",
                    (setting_id,)
                ).fetchone()
                
                if not existing_setting:
                    logger.warning(f"Настройка с ID {setting_id} не найдена для обновления статуса активности")
                    return False
                    
                # Обновляем статус активности
                conn.execute("""
                UPDATE notification_settings
                SET is_active = ?
                WHERE id = ?
                """, (is_active, setting_id))
                
                logger.info(f"Статус активности настройки обновлен: ID {setting_id}, is_active={is_active}")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка обновления статуса активности настройки: {str(e)}")
            return False
            
    def get_max_days_before(self) -> int:
        """
        Получение максимального количества дней предварительного уведомления.
        
        Returns:
            int: Максимальное количество дней
        """
        try:
            with self._db_manager.get_connection() as conn:
                result = conn.execute("""
                SELECT MAX(days_before) as max_days
                FROM notification_settings
                WHERE is_active = 1
                """).fetchone()
                
                if result and result['max_days'] is not None:
                    return result['max_days']
                else:
                    return 0
                
        except Exception as e:
            logger.error(f"Ошибка получения максимального количества дней: {str(e)}")
            return 0
            
    def get_settings_for_time(self, time_str: str, active_only: bool = True) -> List[NotificationSetting]:
        """
        Получение настроек уведомлений для указанного времени.
        
        Args:
            time_str: Время в формате HH:MM
            active_only: Если True, возвращает только активные настройки
            
        Returns:
            List[NotificationSetting]: Список объектов настроек
        """
        try:
            with self._db_manager.get_connection() as conn:
                query = """
                SELECT 
                    id,
                    template_id,
                    days_before,
                    time,
                    is_active,
                    created_at
                FROM notification_settings
                WHERE time = ?
                """
                
                params = [time_str]
                
                if active_only:
                    query += " AND is_active = 1"
                    
                query += " ORDER BY days_before"
                
                settings_data = conn.execute(query, params).fetchall()
                
                settings = []
                for setting_data in settings_data:
                    settings.append(NotificationSetting(
                        id=setting_data['id'],
                        template_id=setting_data['template_id'],
                        days_before=setting_data['days_before'],
                        time=setting_data['time'],
                        is_active=bool(setting_data['is_active']),
                        created_at=setting_data['created_at']
                    ))
                    
                return settings
                
        except Exception as e:
            logger.error(f"Ошибка получения настроек для времени {time_str}: {str(e)}")
            return [] 