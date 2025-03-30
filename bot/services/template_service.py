"""
Сервис для работы с шаблонами уведомлений.

Этот модуль содержит сервис, предоставляющий бизнес-логику для операций
с шаблонами уведомлений.
"""

import logging
from typing import List, Dict, Optional, Any, Union

from bot.core.base_service import BaseService
from bot.core.models import NotificationTemplate
from bot.repositories.template_repository import TemplateRepository

logger = logging.getLogger(__name__)


class TemplateService(BaseService):
    """
    Сервис для работы с шаблонами уведомлений.
    
    Предоставляет бизнес-логику для операций с шаблонами уведомлений,
    используя TemplateRepository для доступа к данным.
    """
    
    def __init__(self, template_repository: TemplateRepository):
        """
        Инициализация сервиса шаблонов уведомлений.
        
        Args:
            template_repository: Репозиторий шаблонов уведомлений
        """
        super().__init__()
        self.template_repository = template_repository
    
    def get_template_by_id(self, template_id: int) -> Optional[NotificationTemplate]:
        """
        Получение шаблона по ID.
        
        Args:
            template_id: ID шаблона
            
        Returns:
            Шаблон или None, если шаблон не найден
        """
        return self.template_repository.get_template_by_id(template_id)
    
    def get_template_by_name_and_category(self, name: str, category: str) -> Optional[NotificationTemplate]:
        """
        Получение шаблона по имени и категории.
        
        Args:
            name: Имя шаблона
            category: Категория шаблона
            
        Returns:
            Шаблон или None, если шаблон не найден
        """
        return self.template_repository.get_template_by_name_and_category(name, category)
    
    def get_all_templates(self, active_only: bool = False) -> List[NotificationTemplate]:
        """
        Получение всех шаблонов.
        
        Args:
            active_only: Если True, возвращает только активные шаблоны
            
        Returns:
            Список всех шаблонов
        """
        return self.template_repository.get_all_templates(active_only)
    
    def get_templates_by_category(self, category: str, active_only: bool = False) -> List[NotificationTemplate]:
        """
        Получение шаблонов по категории.
        
        Args:
            category: Категория шаблонов
            active_only: Если True, возвращает только активные шаблоны
            
        Returns:
            Список шаблонов указанной категории
        """
        return self.template_repository.get_templates_by_category(category, active_only)
    
    def create_template(self, template: NotificationTemplate) -> Optional[int]:
        """
        Создание нового шаблона.
        
        Args:
            template: Шаблон для создания
            
        Returns:
            ID созданного шаблона или None в случае ошибки
        """
        return self.template_repository.add_template(template)
    
    def update_template(self, template: NotificationTemplate) -> bool:
        """
        Обновление шаблона.
        
        Args:
            template: Обновленный шаблон
            
        Returns:
            True, если обновление прошло успешно, иначе False
        """
        return self.template_repository.update_template(template)
    
    def delete_template(self, template_id: int) -> bool:
        """
        Удаление шаблона.
        
        Args:
            template_id: ID шаблона
            
        Returns:
            True, если удаление прошло успешно, иначе False
        """
        return self.template_repository.delete_template(template_id)
    
    def toggle_template_active(self, template_id: int, is_active: bool) -> bool:
        """
        Изменение статуса активности шаблона.
        
        Args:
            template_id: ID шаблона
            is_active: True - активировать шаблон, False - деактивировать шаблон
            
        Returns:
            True, если изменение прошло успешно, иначе False
        """
        return self.template_repository.toggle_template_active(template_id, is_active)
    
    def get_all_categories(self) -> List[str]:
        """
        Получение всех категорий шаблонов.
        
        Returns:
            Список всех категорий
        """
        return self.template_repository.get_all_categories()
    
    def format_template(self, template: Union[NotificationTemplate, str], context: Dict[str, Any]) -> str:
        """
        Форматирование шаблона с использованием контекста.
        
        Args:
            template: Шаблон для форматирования (объект NotificationTemplate или строка)
            context: Словарь с данными для подстановки в шаблон
            
        Returns:
            Отформатированный текст шаблона
        """
        try:
            # Определяем текст шаблона в зависимости от типа входного параметра
            template_text = template.template if isinstance(template, NotificationTemplate) else template
            
            # Используем стандартный метод format для подстановки значений
            return template_text.format(**context)
        except Exception as e:
            template_name = getattr(template, 'name', 'Unknown') if isinstance(template, NotificationTemplate) else 'Unknown'
            logger.error(f"Ошибка форматирования шаблона {template_name}: {str(e)}")
            return template_text if isinstance(template, str) else template.template
    
    def execute(self, *args, **kwargs) -> Any:
        """
        Выполнение основной бизнес-логики сервиса.
        
        Этот метод является заглушкой для соответствия интерфейсу BaseService.
        
        Args:
            *args: Позиционные аргументы
            **kwargs: Именованные аргументы
            
        Returns:
            Результат выполнения бизнес-логики
        """
        # Заглушка для соответствия интерфейсу BaseService
        return None
    
    def get_template_by_name(self, name: str) -> Optional[NotificationTemplate]:
        """
        Получение шаблона по имени.
        
        Args:
            name: Имя шаблона
            
        Returns:
            Шаблон или None, если шаблон не найден
        """
        templates = self.template_repository.get_all_templates(active_only=True)
        for template in templates:
            if template.name == name:
                return template
        return None 