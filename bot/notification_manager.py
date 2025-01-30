import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import threading
import time
import pytz

from .database import Database
from .message_templates import format_birthday_reminder
from config import DEFAULT_NOTIFICATION_SETTINGS

logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self, bot, db: Database):
        """Инициализация менеджера уведомлений"""
        self.bot = bot
        self.db = db
        self._scheduler_thread = None
        self._stop_flag = False
        self.notification_settings = []
        self._load_notification_settings()
        self._last_sent_notifications = {}  # Кэш отправленных уведомлений
        self.moscow_tz = pytz.timezone('Europe/Moscow')
        logger.info(f"Менеджер уведомлений инициализирован с {len(self.notification_settings)} настройками")

    def _get_current_moscow_time(self) -> datetime:
        """Получить текущее время в московском часовом поясе"""
        return datetime.now(self.moscow_tz)

    def _check_and_send_notifications(self):
        """Проверка и отправка уведомлений на основе текущего времени"""
        try:
            current_time = self._get_current_moscow_time()
            current_hour = current_time.strftime("%H:%M")

            # Перезагрузка настроек и очистка кеша каждые 10 минут
            if current_time.minute % 10 == 0 and current_time.second < 30:
                self._load_notification_settings()
                self._clear_notification_cache()
                logger.info("Перезагрузка настроек и очистка кеша (10-минутный интервал)")

            for setting in self.notification_settings:
                setting_time = setting["time"]
                if setting_time == current_hour:
                    # Получаем предстоящие дни рождения
                    birthdays = self.db.get_upcoming_birthdays(setting['days_before'])

                    if birthdays:
                        # Используем 10-минутный интервал для кеша
                        current_10min = current_time.strftime('%Y%m%d_%H%M')[:-1]  # Округляем до десятков минут
                        cache_key = f"{setting['id']}_{current_10min}"

                        if cache_key not in self._last_sent_notifications:
                            logger.info(f"Отправка уведомлений для настройки: {setting}")
                            self._send_notifications_for_setting(setting)
                            self._last_sent_notifications[cache_key] = True
                            logger.info(f"Уведомления отправлены и закешированы с ключом {cache_key}")
                        else:
                            logger.debug(f"Пропуск отправки: уведомления уже были отправлены в интервале {current_10min}")

        except Exception as e:
            logger.error(f"Ошибка в check_and_send_notifications: {str(e)}")

    def _send_notifications_for_setting(self, setting: Dict):
        """Отправка уведомлений для конкретной настройки"""
        try:
            birthdays = self.db.get_upcoming_birthdays(setting['days_before'])
            template = setting['template']

            # Для каждого именинника отправляем уведомления всем остальным
            for birthday_person in birthdays:
                # Получаем всех пользователей, кроме именинника, у которых:
                # 1. Есть согласие на рассылку (is_subscribed = True)
                # 2. Включены уведомления (is_notifications_enabled = True)
                with self.db.get_connection() as conn:
                    recipients = conn.execute("""
                        SELECT * FROM users 
                        WHERE telegram_id != ? 
                        AND is_subscribed = 1 
                        AND is_notifications_enabled = 1
                    """, (birthday_person['telegram_id'],)).fetchall()

                # Отправляем уведомление каждому получателю
                for recipient in recipients:
                    self._send_birthday_notification(
                        recipient=recipient,
                        birthday_person=birthday_person,
                        template=template,
                        days_before=setting['days_before']
                    )

        except Exception as e:
            logger.error(f"Ошибка отправки уведомлений для настройки {setting}: {str(e)}")

    def _send_birthday_notification(self, recipient: Dict, birthday_person: Dict, template: str, days_before: int):
        """Отправка уведомления о дне рождения конкретному получателю"""
        try:
            # Формируем сообщение с информацией об имениннике
            message = format_birthday_reminder(
                template,
                birthday_person["first_name"],
                birthday_person["last_name"],
                birthday_person["birth_date"],
                days_before
            )

            # Отправляем сообщение с поддержкой HTML-тегов
            self.bot.send_message(
                chat_id=recipient["telegram_id"],
                text=message,
                parse_mode='HTML'
            )

            # Логируем успешную отправку
            self.db.log_notification(
                recipient["id"],
                message,
                "success"
            )

        except Exception as e:
            error_msg = f"Ошибка отправки уведомления пользователю {recipient['telegram_id']}"
            logger.error(f"{error_msg}: {str(e)}")
            self.db.log_notification(
                recipient["id"],
                message if 'message' in locals() else "Ошибка до создания сообщения",
                "error",
                error_msg
            )

    def _load_notification_settings(self):
        """Загрузка настроек уведомлений из базы данных"""
        try:
            settings = self.db.get_notification_settings()
            if settings:
                self.notification_settings = settings
                logger.info(f"Загружено {len(settings)} настроек уведомлений")
            else:
                logger.warning("В базе данных не найдены настройки уведомлений")
                self.notification_settings = []
        except Exception as e:
            logger.error(f"Ошибка загрузки настроек уведомлений: {str(e)}")
            self.notification_settings = []

    def _run_scheduler(self):
        """Запуск планировщика уведомлений"""
        logger.info("Запуск планировщика уведомлений")
        while not self._stop_flag:
            try:
                self._check_and_send_notifications()
                time.sleep(60)  # Проверка каждую минуту
            except Exception as e:
                logger.error(f"Ошибка в планировщике уведомлений: {str(e)}")
                time.sleep(60)  # При ошибке ждем минуту перед следующей попыткой

    def start(self):
        """Запуск менеджера уведомлений"""
        logger.info("Запуск NotificationManager")
        if not self._scheduler_thread or not self._scheduler_thread.is_alive():
            self._stop_flag = False
            self._scheduler_thread = threading.Thread(target=self._run_scheduler)
            self._scheduler_thread.daemon = True
            self._scheduler_thread.start()
            logger.info("NotificationManager успешно запущен")

    def stop(self):
        """Остановка менеджера уведомлений"""
        logger.info("Остановка NotificationManager")
        self._stop_flag = True
        if self._scheduler_thread:
            self._scheduler_thread.join()
        logger.info("NotificationManager остановлен")

    def force_send_notification(self, user_id: int, template: str, parse_mode: str = 'HTML') -> bool:
        """Принудительная отправка уведомления конкретному пользователю"""
        try:
            user = self.db.get_user(user_id)
            if not user:
                logger.error(f"Пользователь {user_id} не найден")
                return False

            message = format_birthday_reminder(
                template,
                user["first_name"],
                user["last_name"],
                user["birth_date"],
                0  # days_before=0 для мгновенных уведомлений
            )

            self.bot.send_message(
                chat_id=user["telegram_id"],
                text=message,
                parse_mode=parse_mode or 'HTML'
            )

            self.db.log_notification(
                user["id"],
                message,
                "success"
            )
            logger.info(f"Успешно отправлено принудительное уведомление пользователю {user_id}")
            return True

        except Exception as e:
            logger.error(f"Ошибка принудительной отправки уведомления: {str(e)}")
            return False

    def _clear_notification_cache(self):
        """Очистка кеша отправленных уведомлений"""
        try:
            current_time = self._get_current_moscow_time()
            current_10min = current_time.strftime('%Y%m%d_%H%M')[:-1]  # Округляем до десятков минут

            # Оставляем только записи текущего 10-минутного интервала
            self._last_sent_notifications = {
                key: value for key, value in self._last_sent_notifications.items()
                if key.split('_')[1] == current_10min
            }

            logger.info(f"Очищен кеш уведомлений, осталось {len(self._last_sent_notifications)} записей")
        except Exception as e:
            logger.error(f"Ошибка при очистке кеша уведомлений: {str(e)}")
            self._last_sent_notifications = {}  # При ошибке полностью очищаем кеш

    def reload_settings(self):
        """Публичный метод для перезагрузки настроек уведомлений"""
        logger.info("Принудительная перезагрузка настроек уведомлений")
        self._load_notification_settings()