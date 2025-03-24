"""
Сервис для управления оповещениями пользователей.

Этот модуль содержит сервис, предоставляющий бизнес-логику для отправки
и управления оповещениями пользователей.
"""

import logging
from typing import List, Dict, Optional, Any, Callable, Union
from datetime import date, datetime, timedelta

from bot.core.base_service import BaseService
from bot.core.models import User, NotificationTemplate, NotificationSetting, NotificationLog
from bot.services.user_service import UserService
from bot.services.template_service import TemplateService
from bot.services.notification_setting_service import NotificationSettingService
from bot.services.notification_log_service import NotificationLogService

logger = logging.getLogger(__name__)


class NotificationService(BaseService):
    """
    Сервис для управления оповещениями пользователей.
    
    Предоставляет бизнес-логику для отправки и управления оповещениями,
    используя другие сервисы для получения необходимых данных.
    """
    
    def __init__(
        self,
        user_service: UserService,
        template_service: TemplateService,
        setting_service: NotificationSettingService,
        log_service: NotificationLogService,
        send_message_func: Callable[[int, str], bool] = None
    ):
        """
        Инициализация сервиса оповещений.
        
        Args:
            user_service: Сервис пользователей
            template_service: Сервис шаблонов оповещений
            setting_service: Сервис настроек оповещений
            log_service: Сервис журнала оповещений
            send_message_func: Функция для отправки сообщений
        """
        super().__init__()
        self.user_service = user_service
        self.template_service = template_service
        self.setting_service = setting_service
        self.log_service = log_service
        self.send_message_func = send_message_func
    
    def set_send_function(self, send_message_func: Callable[[int, str], bool]):
        """
        Установка функции для отправки сообщений.
        
        Args:
            send_message_func: Функция для отправки сообщений пользователям
        """
        self.send_message_func = send_message_func
    
    def send_notification(
        self, 
        user_id: int, 
        template_name: str, 
        context: Dict[str, Any] = None
    ) -> bool:
        """
        Отправка оповещения пользователю.
        
        Args:
            user_id: ID пользователя
            template_name: Имя шаблона оповещения
            context: Контекст для форматирования шаблона
            
        Returns:
            True, если оповещение успешно отправлено, иначе False
        """
        if not self.send_message_func:
            logger.error("Функция отправки сообщений не установлена")
            return False
        
        try:
            # Проверяем, что пользователь существует и у него включены оповещения
            user = self.user_service.get_user_by_telegram_id(user_id)
            if not user:
                logger.warning(f"Пользователь с ID {user_id} не найден")
                return False
            
            if not user.get('notifications_enabled'):
                logger.info(f"Оповещения отключены для пользователя {user_id}")
                return False
            
            # Получаем шаблон оповещения
            template = self.template_service.get_template_by_name(template_name)
            if not template:
                logger.warning(f"Шаблон оповещения '{template_name}' не найден")
                return False
            
            # Форматируем шаблон с контекстом
            context = context or {}
            message = self.template_service.format_template(template.get('text', ''), context)
            
            # Отправляем сообщение
            result = self.send_message_func(user_id, message)
            
            # Логируем результат
            if result:
                self.log_service.log_notification(user_id, message, "success")
                logger.info(f"Оповещение успешно отправлено пользователю {user_id}")
            else:
                self.log_service.log_notification(user_id, message, "error", "Ошибка отправки сообщения")
                logger.error(f"Ошибка отправки оповещения пользователю {user_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при отправке оповещения пользователю {user_id}: {e}")
            self.log_service.log_notification(user_id, f"Шаблон: {template_name}", "error", str(e))
            return False
    
    def send_notification_to_all(
        self, 
        template_name: str, 
        context: Dict[str, Any] = None,
        exclude_ids: List[int] = None
    ) -> Dict[str, int]:
        """
        Отправка оповещения всем пользователям.
        
        Args:
            template_name: Имя шаблона оповещения
            context: Контекст для форматирования шаблона
            exclude_ids: Список ID пользователей, которым не нужно отправлять оповещение
            
        Returns:
            Словарь с количеством успешных и неуспешных отправок
        """
        if not self.send_message_func:
            logger.error("Функция отправки сообщений не установлена")
            return {"success": 0, "failed": 0}
        
        try:
            # Получаем всех пользователей с включенными оповещениями
            users = self.user_service.get_all_users()
            
            exclude_ids = exclude_ids or []
            results = {"success": 0, "failed": 0}
            
            for user in users:
                user_id = user.get('telegram_id')
                
                # Пропускаем пользователей из исключений
                if user_id in exclude_ids:
                    continue
                
                # Пропускаем пользователей с отключенными оповещениями
                if not user.get('notifications_enabled'):
                    continue
                
                # Отправляем оповещение
                if self.send_notification(user_id, template_name, context):
                    results["success"] += 1
                else:
                    results["failed"] += 1
            
            logger.info(f"Результат массовой рассылки: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Ошибка при массовой рассылке: {e}")
            return {"success": 0, "failed": 0}
    
    def send_notification_to_users(
        self, 
        user_ids: List[int], 
        template_name: str, 
        context: Dict[str, Any] = None
    ) -> Dict[str, int]:
        """
        Отправка оповещения списку пользователей.
        
        Args:
            user_ids: Список ID пользователей
            template_name: Имя шаблона оповещения
            context: Контекст для форматирования шаблона
            
        Returns:
            Словарь с количеством успешных и неуспешных отправок
        """
        if not self.send_message_func:
            logger.error("Функция отправки сообщений не установлена")
            return {"success": 0, "failed": 0}
        
        try:
            results = {"success": 0, "failed": 0}
            
            for user_id in user_ids:
                if self.send_notification(user_id, template_name, context):
                    results["success"] += 1
                else:
                    results["failed"] += 1
            
            logger.info(f"Результат рассылки группе пользователей: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Ошибка при рассылке группе пользователей: {e}")
            return {"success": 0, "failed": 0}
    
    def send_birthday_notifications(self, days_ahead: int = None) -> Dict[str, int]:
        """
        Отправка оповещений о днях рождения.
        
        Args:
            days_ahead: Количество дней вперед для проверки
                        (если None, будет использовано максимальное значение из настроек)
            
        Returns:
            Словарь с количеством успешных и неуспешных отправок
        """
        try:
            # Если days_ahead не указан, получаем его из настроек
            if days_ahead is None:
                days_ahead = self.setting_service.get_max_days_before()
            
            # Получаем пользователей с приближающимися днями рождения
            birthdays_by_date = self.user_service.get_users_with_birthdays(days_ahead)
            
            if not birthdays_by_date:
                logger.info(f"Нет приближающихся дней рождения в течение {days_ahead} дней")
                return {"success": 0, "failed": 0}
            
            # Для каждой даты отправляем уведомления согласно настройкам
            results = {"success": 0, "failed": 0}
            today = datetime.now().date()
            
            for birthday_date_str, users in birthdays_by_date.items():
                try:
                    birthday_date = datetime.strptime(birthday_date_str, "%Y-%m-%d").date()
                    days_until = (birthday_date - today).days
                    
                    # Получаем настройки оповещений для данного количества дней
                    settings = self.setting_service.get_settings_for_time(days_until)
                    
                    if not settings:
                        logger.info(f"Нет настроек оповещений для {days_until} дней до дня рождения")
                        continue
                    
                    # Для каждой настройки отправляем оповещения
                    for setting in settings:
                        template_id = setting.get('template_id')
                        template = self.template_service.get_template_by_id(template_id)
                        
                        if not template:
                            logger.warning(f"Шаблон с ID {template_id} не найден")
                            continue
                        
                        template_name = template.get('name')
                        
                        # Для каждого пользователя с ДР в эту дату отправляем оповещения всем остальным
                        for birthday_user in users:
                            # Подготавливаем контекст для шаблона
                            context = {
                                'name': birthday_user.get('name', ''),
                                'username': birthday_user.get('username', ''),
                                'date': birthday_date_str,
                                'days_until': days_until
                            }
                            
                            # Отправляем всем пользователям, кроме именинника
                            exclude_ids = [birthday_user.get('telegram_id')]
                            result = self.send_notification_to_all(template_name, context, exclude_ids)
                            
                            results["success"] += result["success"]
                            results["failed"] += result["failed"]
                except Exception as e:
                    logger.error(f"Ошибка при обработке дня рождения {birthday_date_str}: {e}")
            
            logger.info(f"Результат рассылки оповещений о днях рождения: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Ошибка при рассылке оповещений о днях рождения: {e}")
            return {"success": 0, "failed": 0}
    
    def send_notifications_for_current_time(self) -> Dict[str, int]:
        """
        Отправка оповещений, соответствующих текущему времени.
        
        Returns:
            Словарь с количеством успешных и неуспешных отправок
        """
        try:
            # Получаем настройки оповещений для текущего времени
            settings = self.setting_service.get_settings_for_current_time()
            
            if not settings:
                logger.info("Нет настроек оповещений для текущего времени")
                return {"success": 0, "failed": 0}
            
            # Отправляем оповещения согласно каждой настройке
            results = {"success": 0, "failed": 0}
            
            for setting in settings:
                template_id = setting.get('template_id')
                template = self.template_service.get_template_by_id(template_id)
                
                if not template:
                    logger.warning(f"Шаблон с ID {template_id} не найден")
                    continue
                
                template_name = template.get('name')
                
                # Получаем пользователей с приближающимися днями рождения
                days_ahead = setting.get('days_before')
                birthdays_by_date = self.user_service.get_users_with_birthdays(days_ahead)
                
                if not birthdays_by_date:
                    logger.info(f"Нет приближающихся дней рождения в течение {days_ahead} дней")
                    continue
                
                # Для каждой даты отправляем уведомления
                today = datetime.now().date()
                
                for birthday_date_str, users in birthdays_by_date.items():
                    try:
                        birthday_date = datetime.strptime(birthday_date_str, "%Y-%m-%d").date()
                        days_until = (birthday_date - today).days
                        
                        # Если настройка не соответствует текущему количеству дней, пропускаем
                        if days_until != setting.get('days_before'):
                            continue
                        
                        # Для каждого пользователя с ДР в эту дату отправляем оповещения всем остальным
                        for birthday_user in users:
                            # Подготавливаем контекст для шаблона
                            context = {
                                'name': birthday_user.get('name', ''),
                                'username': birthday_user.get('username', ''),
                                'date': birthday_date_str,
                                'days_until': days_until
                            }
                            
                            # Отправляем всем пользователям, кроме именинника
                            exclude_ids = [birthday_user.get('telegram_id')]
                            result = self.send_notification_to_all(template_name, context, exclude_ids)
                            
                            results["success"] += result["success"]
                            results["failed"] += result["failed"]
                    except Exception as e:
                        logger.error(f"Ошибка при обработке дня рождения {birthday_date_str}: {e}")
            
            logger.info(f"Результат рассылки оповещений для текущего времени: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Ошибка при рассылке оповещений для текущего времени: {e}")
            return {"success": 0, "failed": 0}
    
    def execute(self, *args, **kwargs) -> Any:
        """
        Выполнение основной бизнес-логики сервиса.
        
        По умолчанию отправляет оповещения для текущего времени.
        
        Args:
            *args: Позиционные аргументы
            **kwargs: Именованные аргументы
            
        Returns:
            Результат выполнения бизнес-логики
        """
        return self.send_notifications_for_current_time() 