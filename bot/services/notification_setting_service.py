"""
Сервис для работы с настройками уведомлений.

Этот модуль содержит сервис, предоставляющий бизнес-логику для операций
с настройками уведомлений.
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from bot.core.base_service import BaseService
from bot.core.models import NotificationSetting, NotificationTemplate
from bot.repositories.notification_setting_repository import NotificationSettingRepository
from bot.repositories.template_repository import TemplateRepository

logger = logging.getLogger(__name__)


class NotificationSettingService(BaseService):
    """
    Сервис для работы с настройками уведомлений.
    
    Предоставляет бизнес-логику для операций с настройками уведомлений,
    используя NotificationSettingRepository для доступа к данным.
    """
    
    def __init__(self, 
                 setting_repository: NotificationSettingRepository,
                 template_repository: TemplateRepository = None):
        """
        Инициализация сервиса настроек уведомлений.
        
        Args:
            setting_repository: Репозиторий настроек уведомлений
            template_repository: Репозиторий шаблонов уведомлений (опционально)
        """
        super().__init__()
        self.setting_repository = setting_repository
        self.template_repository = template_repository
    
    def get_setting_by_id(self, setting_id: int) -> Optional[NotificationSetting]:
        """
        Получение настройки по ID.
        
        Args:
            setting_id: ID настройки
            
        Returns:
            Настройка или None, если настройка не найдена
        """
        return self.setting_repository.get_setting_by_id(setting_id)
    
    def get_all_settings(self, active_only: bool = False) -> List[NotificationSetting]:
        """
        Получение всех настроек.
        
        Args:
            active_only: Если True, возвращает только активные настройки
            
        Returns:
            Список всех настроек
        """
        return self.setting_repository.get_all_settings(active_only)
    
    def get_settings_by_template_id(self, template_id: int, active_only: bool = False) -> List[NotificationSetting]:
        """
        Получение настроек по ID шаблона.
        
        Args:
            template_id: ID шаблона
            active_only: Если True, возвращает только активные настройки
            
        Returns:
            Список настроек для указанного шаблона
        """
        return self.setting_repository.get_settings_by_template_id(template_id, active_only)
    
    def get_settings_with_templates(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """
        Получение настроек вместе с их шаблонами.
        
        Args:
            active_only: Если True, возвращает только активные настройки
            
        Returns:
            Список словарей, содержащих настройки и шаблоны
        """
        return self.setting_repository.get_settings_with_templates(active_only)
    
    def create_setting(self, setting: NotificationSetting) -> Optional[int]:
        """
        Создание новой настройки.
        
        Args:
            setting: Настройка для создания
            
        Returns:
            ID созданной настройки или None в случае ошибки
        """
        return self.setting_repository.add_setting(setting)
    
    def update_setting(self, setting: NotificationSetting) -> bool:
        """
        Обновление настройки.
        
        Args:
            setting: Обновленная настройка
            
        Returns:
            True, если обновление прошло успешно, иначе False
        """
        return self.setting_repository.update_setting(setting)
    
    def delete_setting(self, setting_id: int) -> bool:
        """
        Удаление настройки.
        
        Args:
            setting_id: ID настройки
            
        Returns:
            True, если удаление прошло успешно, иначе False
        """
        return self.setting_repository.delete_setting(setting_id)
    
    def toggle_setting_active(self, setting_id: int, is_active: bool) -> bool:
        """
        Изменение статуса активности настройки.
        
        Args:
            setting_id: ID настройки
            is_active: True - активировать настройку, False - деактивировать настройку
            
        Returns:
            True, если изменение прошло успешно, иначе False
        """
        return self.setting_repository.toggle_setting_active(setting_id, is_active)
    
    def get_max_days_before(self) -> int:
        """
        Получение максимального количества дней предварительного уведомления.
        
        Returns:
            Максимальное количество дней
        """
        return self.setting_repository.get_max_days_before()
    
    def get_settings_for_time(self, time_str: str, active_only: bool = True) -> List[NotificationSetting]:
        """
        Получение настроек для указанного времени.
        
        Args:
            time_str: Время в формате HH:MM
            active_only: Если True, возвращает только активные настройки
            
        Returns:
            Список настроек для указанного времени
        """
        return self.setting_repository.get_settings_for_time(time_str, active_only)
    
    def get_settings_for_current_time(self, tolerance_minutes: int = 5, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Получение настроек для текущего времени с указанным допуском.
        
        Args:
            tolerance_minutes: Допуск в минутах
            active_only: Если True, возвращает только активные настройки
            
        Returns:
            Список словарей, содержащих настройки и шаблоны
        """
        current_time = datetime.now()
        current_time_str = current_time.strftime("%H:%M")
        
        settings = self.setting_repository.get_settings_for_time(current_time_str, active_only)
        
        if not settings and tolerance_minutes > 0:
            # Если настройки не найдены и указан допуск, ищем в диапазоне
            all_settings = self.setting_repository.get_all_settings(active_only)
            
            # Фильтруем настройки по времени с учетом допуска
            settings = []
            for setting in all_settings:
                setting_time = datetime.strptime(setting.time, "%H:%M").time()
                setting_datetime = datetime.combine(current_time.date(), setting_time)
                
                # Вычисляем разницу во времени в минутах
                time_diff = abs((current_time - setting_datetime).total_seconds() / 60)
                
                if time_diff <= tolerance_minutes:
                    settings.append(setting)
        
        # Если указан репозиторий шаблонов, подгружаем шаблоны
        if settings and self.template_repository:
            result = []
            for setting in settings:
                template = self.template_repository.get_template_by_id(setting.template_id)
                if template:
                    result.append({
                        'setting': setting,
                        'template': template
                    })
            return result
            
        return settings
    
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