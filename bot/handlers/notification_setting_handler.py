"""
Обработчики команд для управления настройками уведомлений.

Этот модуль содержит обработчики для команд бота,
связанных с созданием, редактированием и удалением настроек уведомлений.
"""

import logging
import telebot
from telebot import types
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, time

from bot.core.models import NotificationSetting
from bot.services.notification_setting_service import NotificationSettingService
from bot.services.template_service import TemplateService
from bot.constants import EMOJI, ERROR_MESSAGES
from .base_handler import BaseHandler
from .decorators import admin_required, log_errors, command_args

logger = logging.getLogger(__name__)


class NotificationSettingHandler(BaseHandler):
    """
    Обработчик команд для управления настройками уведомлений.
    
    Обрабатывает команды, связанные с созданием, редактированием и удалением
    настроек уведомлений.
    """
    
    def __init__(self, bot: telebot.TeleBot, 
                 setting_service: NotificationSettingService,
                 template_service: TemplateService):
        """
        Инициализация обработчика настроек уведомлений.
        
        Args:
            bot: Экземпляр бота Telegram
            setting_service: Сервис для работы с настройками уведомлений
            template_service: Сервис для работы с шаблонами уведомлений
        """
        super().__init__(bot)
        self.setting_service = setting_service
        self.template_service = template_service
        
    def register_handlers(self) -> None:
        """Регистрация обработчиков команд для управления настройками уведомлений."""
        # Команды для работы с настройками уведомлений
        self.bot.message_handler(commands=['get_settings'])(self.get_settings)
        self.bot.message_handler(commands=['set_setting'])(self.set_setting)
        self.bot.message_handler(commands=['update_setting'])(self.update_setting)
        self.bot.message_handler(commands=['delete_setting'])(self.delete_setting)
        self.bot.message_handler(commands=['activate_setting'])(self.activate_setting)
        self.bot.message_handler(commands=['deactivate_setting'])(self.deactivate_setting)
        self.bot.message_handler(commands=['help_settings'])(self.help_settings)
        
        # Обработчики callback-запросов для команд
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_get_settings')(self.cmd_get_settings_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_set_setting')(self.cmd_set_setting_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_update_setting')(self.cmd_update_setting_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_delete_setting')(self.cmd_delete_setting_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_activate_setting')(self.cmd_activate_setting_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_deactivate_setting')(self.cmd_deactivate_setting_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_help_settings')(self.cmd_help_settings_callback)
    
    @admin_required
    @log_errors
    def get_settings(self, message: types.Message) -> None:
        """
        Обработчик команды /get_settings.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            # Получаем все настройки с информацией о шаблонах
            settings = self.setting_service.get_settings_with_templates()
            
            if not settings:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['info']} В системе нет настроек уведомлений."
                )
                return
            
            # Формируем сообщение со списком настроек
            settings_text = f"{EMOJI['setting']} <b>Список настроек уведомлений ({len(settings)}):</b>\n\n"
            
            for setting in settings:
                setting_id = setting.get('id')
                template_id = setting.get('template_id')
                template_name = setting.get('template_name', 'Неизвестный шаблон')
                days_before = setting.get('days_before', 0)
                time_str = setting.get('time', '12:00')
                is_active = setting.get('is_active', True)
                
                status_emoji = EMOJI['active'] if is_active else EMOJI['inactive']
                
                setting_text = (
                    f"{status_emoji} <b>ID {setting_id}</b>\n"
                    f"Шаблон: {template_name} (ID: {template_id})\n"
                    f"Дней до события: {days_before}\n"
                    f"Время отправки: {time_str}\n\n"
                )
                
                settings_text += setting_text
            
            self.send_message(message.chat.id, settings_text)
            logger.info(f"Отправлен список настроек администратору {message.from_user.id}")
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка настроек: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    def set_setting(self, message: types.Message) -> None:
        """
        Обработчик команды /set_setting.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            
            if len(args) < 3:
                self.send_message(
                    message.chat.id, 
                    f"{EMOJI['error']} <b>Ошибка:</b> Неверный формат команды.\n\n"
                    f"Используйте: <code>/set_setting [id_шаблона] [дней_до_события] [время_отправки]</code>\n\n"
                    f"Например: <code>/set_setting 1 1 12:00</code>"
                )
                return
            
            # Извлекаем аргументы
            try:
                template_id = int(args[0])
                days_before = int(args[1])
                time_str = args[2]
            except ValueError:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> ID шаблона и дни до события должны быть числами."
                )
                return
            
            # Проверяем формат времени
            try:
                hour, minute = map(int, time_str.split(':'))
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError("Неверный формат времени")
            except ValueError:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Неверный формат времени. Используйте формат HH:MM (например, 12:30)."
                )
                return
            
            # Проверяем существование шаблона
            template = self.template_service.get_template_by_id(template_id)
            if not template:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Шаблон с ID {template_id} не найден."
                )
                return
            
            # Создаем настройку
            setting = NotificationSetting(
                template_id=template_id,
                days_before=days_before,
                time=time_str,
                is_active=True
            )
            
            # Добавляем настройку в базу
            result = self.setting_service.create_setting(setting)
            
            if result:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['success']} Настройка уведомления успешно добавлена."
                )
                logger.info(f"Добавлена настройка уведомления администратором {message.from_user.id}")
            else:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Не удалось добавить настройку."
                )
                
        except Exception as e:
            logger.error(f"Ошибка при добавлении настройки: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    @command_args(4)
    def update_setting(self, message: types.Message, args: List[str]) -> None:
        """
        Обработчик команды /update_setting.
        
        Args:
            message: Сообщение от пользователя
            args: Аргументы команды
        """
        try:
            # Извлекаем аргументы
            try:
                setting_id = int(args[0])
                template_id = int(args[1])
                days_before = int(args[2])
                time_str = args[3]
            except ValueError:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> ID настройки, ID шаблона и дни до события должны быть числами."
                )
                return
            
            # Проверяем формат времени
            try:
                hour, minute = map(int, time_str.split(':'))
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError("Неверный формат времени")
            except ValueError:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Неверный формат времени. Используйте формат HH:MM (например, 12:30)."
                )
                return
            
            # Получаем настройку из базы
            setting = self.setting_service.get_setting_by_id(setting_id)
            
            if not setting:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Настройка с ID {setting_id} не найдена."
                )
                return
            
            # Проверяем существование шаблона
            template = self.template_service.get_template_by_id(template_id)
            if not template:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Шаблон с ID {template_id} не найден."
                )
                return
            
            # Обновляем настройку
            setting['template_id'] = template_id
            setting['days_before'] = days_before
            setting['time'] = time_str
            
            result = self.setting_service.update_setting(setting)
            
            if result:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['success']} Настройка с ID {setting_id} успешно обновлена."
                )
                logger.info(f"Обновлена настройка с ID {setting_id} администратором {message.from_user.id}")
            else:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Не удалось обновить настройку."
                )
                
        except Exception as e:
            logger.error(f"Ошибка при обновлении настройки: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    @command_args(1)
    def delete_setting(self, message: types.Message, args: List[str]) -> None:
        """
        Обработчик команды /delete_setting.
        
        Args:
            message: Сообщение от пользователя
            args: Аргументы команды
        """
        try:
            # Извлекаем ID настройки
            try:
                setting_id = int(args[0])
            except ValueError:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> ID настройки должен быть числом."
                )
                return
            
            # Получаем настройку из базы для проверки
            setting = self.setting_service.get_setting_by_id(setting_id)
            
            if not setting:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Настройка с ID {setting_id} не найдена."
                )
                return
            
            # Удаляем настройку
            result = self.setting_service.delete_setting(setting_id)
            
            if result:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['success']} Настройка с ID {setting_id} успешно удалена."
                )
                logger.info(f"Удалена настройка с ID {setting_id} администратором {message.from_user.id}")
            else:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Не удалось удалить настройку."
                )
                
        except Exception as e:
            logger.error(f"Ошибка при удалении настройки: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    @command_args(1)
    def activate_setting(self, message: types.Message, args: List[str]) -> None:
        """
        Обработчик команды /activate_setting.
        
        Args:
            message: Сообщение от пользователя
            args: Аргументы команды
        """
        try:
            # Извлекаем ID настройки
            try:
                setting_id = int(args[0])
            except ValueError:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> ID настройки должен быть числом."
                )
                return
            
            # Получаем настройку из базы для проверки
            setting = self.setting_service.get_setting_by_id(setting_id)
            
            if not setting:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Настройка с ID {setting_id} не найдена."
                )
                return
            
            # Если настройка уже активна, сообщаем об этом
            if setting.get('is_active', False):
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['info']} Настройка с ID {setting_id} уже активна."
                )
                return
            
            # Активируем настройку
            result = self.setting_service.toggle_setting_active(setting_id, True)
            
            if result:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['success']} Настройка с ID {setting_id} успешно активирована."
                )
                logger.info(f"Активирована настройка с ID {setting_id} администратором {message.from_user.id}")
            else:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Не удалось активировать настройку."
                )
                
        except Exception as e:
            logger.error(f"Ошибка при активации настройки: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    @command_args(1)
    def deactivate_setting(self, message: types.Message, args: List[str]) -> None:
        """
        Обработчик команды /deactivate_setting.
        
        Args:
            message: Сообщение от пользователя
            args: Аргументы команды
        """
        try:
            # Извлекаем ID настройки
            try:
                setting_id = int(args[0])
            except ValueError:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> ID настройки должен быть числом."
                )
                return
            
            # Получаем настройку из базы для проверки
            setting = self.setting_service.get_setting_by_id(setting_id)
            
            if not setting:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Настройка с ID {setting_id} не найдена."
                )
                return
            
            # Если настройка уже неактивна, сообщаем об этом
            if not setting.get('is_active', True):
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['info']} Настройка с ID {setting_id} уже неактивна."
                )
                return
            
            # Деактивируем настройку
            result = self.setting_service.toggle_setting_active(setting_id, False)
            
            if result:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['success']} Настройка с ID {setting_id} успешно деактивирована."
                )
                logger.info(f"Деактивирована настройка с ID {setting_id} администратором {message.from_user.id}")
            else:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Не удалось деактивировать настройку."
                )
                
        except Exception as e:
            logger.error(f"Ошибка при деактивации настройки: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    def help_settings(self, message: types.Message) -> None:
        """
        Обработчик команды /help_settings.
        
        Args:
            message: Сообщение от пользователя
        """
        help_text = (
            f"{EMOJI['info']} <b>Справка по командам настроек уведомлений:</b>\n\n"
            f"/get_settings - Получить список всех настроек уведомлений\n"
            f"/set_setting [id_шаблона] [дней_до_события] [время_отправки] - Добавить новую настройку\n"
            f"/update_setting [id] [id_шаблона] [дней_до_события] [время_отправки] - Обновить настройку\n"
            f"/delete_setting [id] - Удалить настройку\n"
            f"/activate_setting [id] - Активировать настройку\n"
            f"/deactivate_setting [id] - Деактивировать настройку\n"
        )
        self.send_message(message.chat.id, help_text)
        logger.info(f"Отправлена справка по настройкам администратору {message.from_user.id}")

    # Обработчики callback-запросов
    
    @log_errors
    def cmd_get_settings_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды get_settings.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.get_settings(call.message)
    
    @log_errors
    def cmd_set_setting_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды set_setting.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.send_message(
            call.message.chat.id,
            f"{EMOJI['info']} Введите команду в формате: <code>/set_setting [id_шаблона] [дней_до_события] [время_отправки]</code>\n\n"
            f"Например: <code>/set_setting 1 1 12:00</code>"
        )
    
    @log_errors
    def cmd_update_setting_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды update_setting.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.send_message(
            call.message.chat.id,
            f"{EMOJI['info']} Введите команду в формате: <code>/update_setting [id] [id_шаблона] [дней_до_события] [время_отправки]</code>\n\n"
            f"Например: <code>/update_setting 1 2 3 15:30</code>"
        )
    
    @log_errors
    def cmd_delete_setting_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды delete_setting.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.send_message(
            call.message.chat.id,
            f"{EMOJI['info']} Введите команду в формате: <code>/delete_setting [id]</code>\n\n"
            f"Например: <code>/delete_setting 1</code>"
        )
    
    @log_errors
    def cmd_activate_setting_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды activate_setting.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.send_message(
            call.message.chat.id,
            f"{EMOJI['info']} Введите команду в формате: <code>/activate_setting [id]</code>\n\n"
            f"Например: <code>/activate_setting 1</code>"
        )
    
    @log_errors
    def cmd_deactivate_setting_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды deactivate_setting.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.send_message(
            call.message.chat.id,
            f"{EMOJI['info']} Введите команду в формате: <code>/deactivate_setting [id]</code>\n\n"
            f"Например: <code>/deactivate_setting 1</code>"
        )
    
    @log_errors
    def cmd_help_settings_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды help_settings.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.help_settings(call.message) 