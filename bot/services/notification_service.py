"""
Сервис для управления оповещениями пользователей.

Этот модуль содержит сервис, предоставляющий бизнес-логику для отправки
и управления оповещениями пользователей.
"""

import logging
import threading
import time
import pytz
from typing import List, Dict, Optional, Any, Callable, Union
from datetime import date, datetime, timedelta

from bot.core.base_service import BaseService
from bot.core.models import User, NotificationTemplate, NotificationSetting, NotificationLog
from bot.services.user_service import UserService
from bot.services.template_service import TemplateService
from bot.services.notification_setting_service import NotificationSettingService
from bot.services.notification_log_service import NotificationLogService
from bot.constants import MONTHS_RU

logger = logging.getLogger(__name__)


class NotificationService(BaseService):
    """
    Сервис для управления оповещениями пользователей.
    
    Предоставляет бизнес-логику для отправки и управления оповещениями,
    используя другие сервисы для получения необходимых данных.
    """
    
    def __init__(
        self,
        bot,
        user_service: UserService,
        template_service: TemplateService,
        setting_service: NotificationSettingService,
        log_service: NotificationLogService
    ):
        """
        Инициализация сервиса оповещений.
        
        Args:
            bot: Экземпляр бота Telegram
            user_service: Сервис пользователей
            template_service: Сервис шаблонов оповещений
            setting_service: Сервис настроек оповещений
            log_service: Сервис журнала оповещений
        """
        super().__init__()
        self.bot = bot
        self.user_service = user_service
        self.template_service = template_service
        self.setting_service = setting_service
        self.log_service = log_service
        
        # Инициализация планировщика уведомлений
        self._scheduler_thread = None
        self._stop_flag = False
        self._last_sent_notifications = {}  # Кэш отправленных уведомлений
        self.moscow_tz = pytz.timezone('Europe/Moscow')
        
        # Определение функции отправки сообщений
        self.send_message_func = self._send_message
    
    def _send_message(self, chat_id: int, text: str, parse_mode: str = 'HTML') -> bool:
        """
        Отправка сообщения через бота.
        
        Args:
            chat_id: Telegram ID чата (совпадает с telegram_id пользователя)
            text: Текст сообщения
            parse_mode: Режим парсинга сообщения
            
        Returns:
            True, если сообщение успешно отправлено, иначе False
        """
        try:
            self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения пользователю {chat_id}: {e}")
            return False
    
    def _get_current_moscow_time(self) -> datetime:
        """
        Получить текущее время в московском часовом поясе.
        
        Returns:
            Текущее время в московском часовом поясе
        """
        return datetime.now(self.moscow_tz)
    
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
        try:
            # Проверяем, что пользователь существует и у него включены оповещения
            user = self.user_service.get_user_by_telegram_id(user_id)
            if not user:
                logger.warning(f"Пользователь с Telegram ID {user_id} не найден")
                return False
            
            if not user.is_notifications_enabled:
                logger.info(f"Оповещения отключены для пользователя {user_id}")
                return False
            
            # Получаем шаблон оповещения
            template = self.template_service.get_template_by_name(template_name)
            if not template:
                logger.warning(f"Шаблон оповещения '{template_name}' не найден")
                return False
            
            # Форматируем шаблон с контекстом
            context = context or {}
            message = self.template_service.format_template(template, context)
            
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
        try:
            # Получаем всех пользователей с включенными оповещениями
            users = self.user_service.get_all_users()
            
            exclude_ids = exclude_ids or []
            results = {"success": 0, "failed": 0}
            
            for user in users:
                telegram_id = user.telegram_id
                
                # Пропускаем пользователей из исключений
                if telegram_id in exclude_ids:
                    continue
                
                # Пропускаем пользователей с отключенными оповещениями
                if not user.is_notifications_enabled:
                    continue
                
                # Отправляем оповещение
                if self.send_notification(telegram_id, template_name, context):
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
                        template = self.template_service.get_template_by_id(setting.template_id)
                        
                        if not template:
                            logger.warning(f"Шаблон с ID {setting.template_id} не найден")
                            continue
                        
                        # Для каждого пользователя с ДР в эту дату отправляем оповещения всем остальным
                        for birthday_user in users:
                            # Форматируем даты с русскими названиями месяцев
                            date_str = f"{birthday_date.day:02d} {MONTHS_RU[birthday_date.month]['gen']}"
                            date_before = birthday_date - timedelta(days=1)
                            date_before_str = f"{date_before.day:02d} {MONTHS_RU[date_before.month]['gen']}"
                            
                            # Получаем значения платежных данных
                            phone_pay = self.setting_service.get_payment_phone()
                            name_pay = self.setting_service.get_payment_name()
                            
                            # Логируем платежные данные для отладки
                            logger.info(f"Платежные данные для уведомления: phone={phone_pay}, name={name_pay}")
                            
                            # Подготавливаем контекст для шаблона
                            context = {
                                'name': f"{birthday_user['first_name']} {birthday_user['last_name']}".strip(),
                                'first_name': birthday_user['first_name'],
                                'last_name': birthday_user['last_name'],
                                'date': date_str,
                                'date_before': date_before_str,
                                'days_until': days_until,
                                'phone_pay': phone_pay,
                                'name_pay': name_pay
                            }
                            
                            # Отправляем всем пользователям, кроме именинника
                            exclude_ids = [birthday_user['telegram_id']]
                            result = self.send_notification_to_all(template.name, context, exclude_ids)
                            
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
            # Получаем текущее время в формате ЧЧ:ММ для сравнения с настройками
            current_time = self._get_current_moscow_time()
            current_hour_minute = current_time.strftime("%H:%M")
            
            # Получаем настройки оповещений для текущего времени
            settings = self.setting_service.get_settings_for_time(current_hour_minute)
            
            if not settings:
                logger.debug(f"Нет настроек оповещений для времени {current_hour_minute}")
                return {"success": 0, "failed": 0}
            
            # Проверяем кэш оповещений - отправляем не чаще раза в 10 минут
            current_10min = current_time.strftime('%Y%m%d_%H%M')[:-1]  # Округляем до десятков минут
            results = {"success": 0, "failed": 0}
            
            for setting in settings:
                setting_id = setting.id
                cache_key = f"{setting_id}_{current_10min}"
                
                if cache_key in self._last_sent_notifications:
                    logger.debug(f"Пропуск отправки: уведомления уже были отправлены в интервале {current_10min}")
                    continue
                
                # Получаем пользователей с приближающимися днями рождения
                days_ahead = setting.days_before
                birthdays_by_date = self.user_service.get_users_with_birthdays(days_ahead)
                
                if not birthdays_by_date:
                    logger.debug(f"Нет приближающихся дней рождения в течение {days_ahead} дней")
                    continue
                
                # Для каждой даты отправляем уведомления
                today = datetime.now().date()
                has_sent = False
                
                for birthday_date_str, users in birthdays_by_date.items():
                    try:
                        birthday_date = datetime.strptime(birthday_date_str, "%Y-%m-%d").date()
                        days_until = (birthday_date - today).days
                        
                        # Если настройка не соответствует текущему количеству дней, пропускаем
                        if days_until != setting.days_before:
                            continue
                        
                        template = self.template_service.get_template_by_id(setting.template_id)
                        
                        if not template:
                            logger.warning(f"Шаблон с ID {setting.template_id} не найден")
                            continue
                        
                        # Для каждого пользователя с ДР в эту дату отправляем оповещения всем остальным
                        for birthday_user in users:
                            # Форматируем даты с русскими названиями месяцев
                            date_str = f"{birthday_date.day:02d} {MONTHS_RU[birthday_date.month]['gen']}"
                            date_before = birthday_date - timedelta(days=1)
                            date_before_str = f"{date_before.day:02d} {MONTHS_RU[date_before.month]['gen']}"
                            
                            # Получаем значения платежных данных
                            phone_pay = self.setting_service.get_payment_phone()
                            name_pay = self.setting_service.get_payment_name()
                            
                            # Логируем платежные данные для отладки
                            logger.info(f"Платежные данные для уведомления: phone={phone_pay}, name={name_pay}")
                            
                            # Подготавливаем контекст для шаблона
                            context = {
                                'name': f"{birthday_user['first_name']} {birthday_user['last_name']}".strip(),
                                'first_name': birthday_user['first_name'],
                                'last_name': birthday_user['last_name'],
                                'date': date_str,
                                'date_before': date_before_str,
                                'days_until': days_until,
                                'phone_pay': phone_pay,
                                'name_pay': name_pay
                            }
                            
                            # Отправляем всем пользователям, кроме именинника
                            exclude_ids = [birthday_user['telegram_id']]
                            result = self.send_notification_to_all(template.name, context, exclude_ids)
                            
                            results["success"] += result["success"]
                            results["failed"] += result["failed"]
                            has_sent = True
                    except Exception as e:
                        logger.error(f"Ошибка при обработке дня рождения {birthday_date_str}: {e}")
                
                # Добавляем запись в кэш только если было отправлено хотя бы одно оповещение
                if has_sent:
                    self._last_sent_notifications[cache_key] = True
            
            logger.info(f"Результат рассылки оповещений для текущего времени: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Ошибка при рассылке оповещений для текущего времени: {e}")
            return {"success": 0, "failed": 0}
    
    def _clear_notification_cache(self):
        """
        Очистка кэша отправленных уведомлений.
        
        Удаляет из кэша записи, которые не относятся к текущему 10-минутному интервалу.
        """
        try:
            current_time = self._get_current_moscow_time()
            current_10min = current_time.strftime('%Y%m%d_%H%M')[:-1]  # Округляем до десятков минут

            # Оставляем только записи текущего 10-минутного интервала
            self._last_sent_notifications = {
                key: value for key, value in self._last_sent_notifications.items()
                if key.split('_')[1] == current_10min
            }

            logger.info(f"Очищен кэш уведомлений, осталось {len(self._last_sent_notifications)} записей")
        except Exception as e:
            logger.error(f"Ошибка при очистке кеша уведомлений: {e}")
            self._last_sent_notifications = {}  # При ошибке полностью очищаем кеш
    
    def _check_and_send_notifications(self):
        """
        Проверка и отправка уведомлений на основе текущего времени.
        
        Выполняется в отдельном потоке для периодической проверки и отправки
        уведомлений в соответствии с настройками.
        """
        try:
            current_time = self._get_current_moscow_time()
            
            # Перезагрузка настроек и очистка кеша каждые 10 минут
            if current_time.minute % 10 == 0 and current_time.second < 30:
                self.setting_service.reload_settings()
                self._clear_notification_cache()
                logger.info("Перезагрузка настроек и очистка кеша (10-минутный интервал)")
            
            # Отправляем уведомления для текущего времени
            self.send_notifications_for_current_time()
            
        except Exception as e:
            logger.error(f"Ошибка в _check_and_send_notifications: {e}")
    
    def _run_scheduler(self):
        """
        Запуск планировщика уведомлений.
        
        Выполняется в отдельном потоке и периодически проверяет необходимость
        отправки уведомлений.
        """
        logger.info("Запуск планировщика уведомлений")
        while not self._stop_flag:
            try:
                self._check_and_send_notifications()
                time.sleep(60)  # Проверка каждую минуту
            except Exception as e:
                logger.error(f"Ошибка в планировщике уведомлений: {e}")
                time.sleep(60)  # При ошибке ждем минуту перед следующей попыткой
    
    def start(self):
        """
        Запуск сервиса отправки уведомлений.
        
        Запускает планировщик в отдельном потоке для периодической
        отправки уведомлений согласно настройкам.
        """
        logger.info("Запуск NotificationService")
        if not self._scheduler_thread or not self._scheduler_thread.is_alive():
            self._stop_flag = False
            self._scheduler_thread = threading.Thread(target=self._run_scheduler)
            self._scheduler_thread.daemon = True
            self._scheduler_thread.start()
            logger.info("NotificationService успешно запущен")
    
    def stop(self):
        """
        Остановка сервиса отправки уведомлений.
        
        Останавливает планировщик уведомлений.
        """
        logger.info("Остановка NotificationService")
        self._stop_flag = True
        if self._scheduler_thread:
            self._scheduler_thread.join()
        logger.info("NotificationService остановлен")
    
    def reload_settings(self):
        """
        Перезагрузка настроек уведомлений.
        
        Обновляет настройки из базы данных.
        """
        logger.info("Принудительная перезагрузка настроек уведомлений")
        self.setting_service.reload_settings()
    
    def force_send_notification(self, user_id: int, template_name: str, context: Dict[str, Any] = None) -> bool:
        """
        Принудительная отправка уведомления конкретному пользователю.
        
        Args:
            user_id: ID пользователя
            template_name: Имя шаблона уведомления
            context: Контекст для форматирования шаблона
            
        Returns:
            True, если уведомление успешно отправлено, иначе False
        """
        return self.send_notification(user_id, template_name, context)
    
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