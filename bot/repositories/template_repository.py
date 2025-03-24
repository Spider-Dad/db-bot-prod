"""
Репозиторий шаблонов уведомлений.

Этот модуль содержит класс TemplateRepository, отвечающий за управление
шаблонами уведомлений в базе данных.
"""

from typing import List, Dict, Optional, Any, Tuple
import logging
import sqlite3

from bot.core.models import NotificationTemplate
from bot.core.base_repository import BaseRepository
from bot.repositories.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class TemplateRepository(BaseRepository):
    """
    Репозиторий для работы с шаблонами уведомлений.
    
    Предоставляет методы для добавления, обновления, удаления и получения информации
    о шаблонах уведомлений из базы данных.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Инициализация репозитория шаблонов уведомлений.
        
        Args:
            db_manager: Менеджер базы данных
        """
        super().__init__(db_manager)
        
    def add_template(self, template: NotificationTemplate) -> Optional[int]:
        """
        Добавление нового шаблона уведомления в базу данных.
        
        Args:
            template: Объект шаблона уведомления для добавления
            
        Returns:
            Optional[int]: ID добавленного шаблона или None в случае ошибки
        """
        try:
            with self._db_manager.get_connection() as conn:
                # Проверяем, существует ли таблица
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
                
                # Проверяем, существует ли шаблон с таким именем и категорией
                existing_template = conn.execute("""
                    SELECT id FROM notification_templates 
                    WHERE name = ? AND category = ?
                """, (template.name, template.category)).fetchone()
                
                if existing_template:
                    # Обновляем существующий шаблон
                    conn.execute("""
                    UPDATE notification_templates
                    SET 
                        template = ?,
                        is_active = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """, (
                        template.template,
                        template.is_active,
                        existing_template['id']
                    ))
                    
                    logger.info(f"Шаблон обновлен: {template.name} ({template.category})")
                    return existing_template['id']
                else:
                    # Добавляем новый шаблон
                    cursor = conn.execute("""
                    INSERT INTO notification_templates (
                        name,
                        template,
                        category,
                        is_active
                    ) VALUES (?, ?, ?, ?)
                    """, (
                        template.name,
                        template.template,
                        template.category,
                        template.is_active
                    ))
                    
                    logger.info(f"Новый шаблон добавлен: {template.name} ({template.category})")
                    return cursor.lastrowid
                    
        except Exception as e:
            logger.error(f"Ошибка добавления шаблона: {str(e)}")
            return None
            
    def delete_template(self, template_id: int) -> bool:
        """
        Удаление шаблона уведомления из базы данных.
        
        Args:
            template_id: ID шаблона для удаления
            
        Returns:
            bool: True, если шаблон удален успешно, иначе False
        """
        try:
            with self._db_manager.get_connection() as conn:
                # Проверяем, существует ли шаблон
                existing_template = conn.execute(
                    "SELECT id FROM notification_templates WHERE id = ?",
                    (template_id,)
                ).fetchone()
                
                if not existing_template:
                    logger.warning(f"Шаблон с ID {template_id} не найден для удаления")
                    return False
                    
                # Проверяем, есть ли связанные настройки уведомлений
                has_settings = conn.execute("""
                    SELECT COUNT(*) FROM notification_settings 
                    WHERE template_id = ?
                """, (template_id,)).fetchone()[0]
                
                if has_settings > 0:
                    # Если есть связанные настройки, просто деактивируем шаблон
                    conn.execute("""
                    UPDATE notification_templates
                    SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """, (template_id,))
                    
                    logger.info(f"Шаблон деактивирован (имеет связанные настройки): ID {template_id}")
                    return True
                else:
                    # Если нет связанных настроек, физически удаляем шаблон
                    conn.execute("DELETE FROM notification_templates WHERE id = ?", (template_id,))
                    logger.info(f"Шаблон удален: ID {template_id}")
                    return True
                
        except Exception as e:
            logger.error(f"Ошибка удаления шаблона: {str(e)}")
            return False
            
    def get_template_by_id(self, template_id: int) -> Optional[NotificationTemplate]:
        """
        Получение шаблона уведомления по его ID.
        
        Args:
            template_id: ID шаблона
            
        Returns:
            Optional[NotificationTemplate]: Объект шаблона или None, если шаблон не найден
        """
        try:
            with self._db_manager.get_connection() as conn:
                template_data = conn.execute("""
                SELECT 
                    id,
                    name,
                    template,
                    category,
                    created_at,
                    updated_at,
                    is_active
                FROM notification_templates
                WHERE id = ?
                """, (template_id,)).fetchone()
                
                if not template_data:
                    return None
                    
                return NotificationTemplate(
                    id=template_data['id'],
                    name=template_data['name'],
                    template=template_data['template'],
                    category=template_data['category'],
                    is_active=bool(template_data['is_active']),
                    created_at=template_data['created_at'],
                    updated_at=template_data['updated_at']
                )
                
        except Exception as e:
            logger.error(f"Ошибка получения шаблона: {str(e)}")
            return None
            
    def get_template_by_name_and_category(self, name: str, category: str) -> Optional[NotificationTemplate]:
        """
        Получение шаблона уведомления по его имени и категории.
        
        Args:
            name: Имя шаблона
            category: Категория шаблона
            
        Returns:
            Optional[NotificationTemplate]: Объект шаблона или None, если шаблон не найден
        """
        try:
            with self._db_manager.get_connection() as conn:
                template_data = conn.execute("""
                SELECT 
                    id,
                    name,
                    template,
                    category,
                    created_at,
                    updated_at,
                    is_active
                FROM notification_templates
                WHERE name = ? AND category = ?
                """, (name, category)).fetchone()
                
                if not template_data:
                    return None
                    
                return NotificationTemplate(
                    id=template_data['id'],
                    name=template_data['name'],
                    template=template_data['template'],
                    category=template_data['category'],
                    is_active=bool(template_data['is_active']),
                    created_at=template_data['created_at'],
                    updated_at=template_data['updated_at']
                )
                
        except Exception as e:
            logger.error(f"Ошибка получения шаблона: {str(e)}")
            return None
            
    def get_all_templates(self, active_only: bool = False) -> List[NotificationTemplate]:
        """
        Получение всех шаблонов уведомлений из базы данных.
        
        Args:
            active_only: Если True, возвращает только активные шаблоны
            
        Returns:
            List[NotificationTemplate]: Список объектов шаблонов
        """
        try:
            with self._db_manager.get_connection() as conn:
                query = """
                SELECT 
                    id,
                    name,
                    template,
                    category,
                    created_at,
                    updated_at,
                    is_active
                FROM notification_templates
                """
                
                if active_only:
                    query += " WHERE is_active = 1"
                    
                query += " ORDER BY category, name"
                
                templates_data = conn.execute(query).fetchall()
                
                templates = []
                for template_data in templates_data:
                    templates.append(NotificationTemplate(
                        id=template_data['id'],
                        name=template_data['name'],
                        template=template_data['template'],
                        category=template_data['category'],
                        is_active=bool(template_data['is_active']),
                        created_at=template_data['created_at'],
                        updated_at=template_data['updated_at']
                    ))
                    
                return templates
                
        except Exception as e:
            logger.error(f"Ошибка получения всех шаблонов: {str(e)}")
            return []
            
    def get_templates_by_category(self, category: str, active_only: bool = False) -> List[NotificationTemplate]:
        """
        Получение шаблонов уведомлений по категории.
        
        Args:
            category: Категория шаблонов
            active_only: Если True, возвращает только активные шаблоны
            
        Returns:
            List[NotificationTemplate]: Список объектов шаблонов
        """
        try:
            with self._db_manager.get_connection() as conn:
                query = """
                SELECT 
                    id,
                    name,
                    template,
                    category,
                    created_at,
                    updated_at,
                    is_active
                FROM notification_templates
                WHERE category = ?
                """
                
                params = [category]
                
                if active_only:
                    query += " AND is_active = 1"
                    
                query += " ORDER BY name"
                
                templates_data = conn.execute(query, params).fetchall()
                
                templates = []
                for template_data in templates_data:
                    templates.append(NotificationTemplate(
                        id=template_data['id'],
                        name=template_data['name'],
                        template=template_data['template'],
                        category=template_data['category'],
                        is_active=bool(template_data['is_active']),
                        created_at=template_data['created_at'],
                        updated_at=template_data['updated_at']
                    ))
                    
                return templates
                
        except Exception as e:
            logger.error(f"Ошибка получения шаблонов по категории: {str(e)}")
            return []
            
    def update_template(self, template: NotificationTemplate) -> bool:
        """
        Обновление информации о шаблоне уведомления.
        
        Args:
            template: Объект шаблона с обновленными данными
            
        Returns:
            bool: True, если обновление прошло успешно, иначе False
        """
        try:
            with self._db_manager.get_connection() as conn:
                # Проверяем, существует ли шаблон
                existing_template = conn.execute(
                    "SELECT id FROM notification_templates WHERE id = ?",
                    (template.id,)
                ).fetchone()
                
                if not existing_template:
                    logger.warning(f"Шаблон с ID {template.id} не найден для обновления")
                    return False
                    
                # Обновляем шаблон
                conn.execute("""
                UPDATE notification_templates
                SET 
                    name = ?,
                    template = ?,
                    category = ?,
                    is_active = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """, (
                    template.name,
                    template.template,
                    template.category,
                    template.is_active,
                    template.id
                ))
                
                logger.info(f"Шаблон обновлен: {template.name} ({template.category})")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка обновления шаблона: {str(e)}")
            return False
            
    def toggle_template_active(self, template_id: int, is_active: bool) -> bool:
        """
        Изменение статуса активности шаблона уведомления.
        
        Args:
            template_id: ID шаблона
            is_active: Новый статус активности
            
        Returns:
            bool: True, если обновление прошло успешно, иначе False
        """
        try:
            with self._db_manager.get_connection() as conn:
                # Проверяем, существует ли шаблон
                existing_template = conn.execute(
                    "SELECT id FROM notification_templates WHERE id = ?",
                    (template_id,)
                ).fetchone()
                
                if not existing_template:
                    logger.warning(f"Шаблон с ID {template_id} не найден для обновления статуса активности")
                    return False
                    
                # Обновляем статус активности
                conn.execute("""
                UPDATE notification_templates
                SET 
                    is_active = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """, (is_active, template_id))
                
                logger.info(f"Статус активности шаблона обновлен: ID {template_id}, is_active={is_active}")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка обновления статуса активности шаблона: {str(e)}")
            return False
            
    def get_all_categories(self) -> List[str]:
        """
        Получение всех категорий шаблонов уведомлений.
        
        Returns:
            List[str]: Список категорий
        """
        try:
            with self._db_manager.get_connection() as conn:
                categories = conn.execute("""
                SELECT DISTINCT category
                FROM notification_templates
                ORDER BY category
                """).fetchall()
                
                return [category['category'] for category in categories]
                
        except Exception as e:
            logger.error(f"Ошибка получения категорий шаблонов: {str(e)}")
            return [] 