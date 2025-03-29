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
        self.bot.register_message_handler(self.get_settings, commands=['get_settings'])
        self.bot.register_message_handler(self.set_setting, commands=['set_setting'])
        self.bot.register_message_handler(self.update_setting, commands=['update_setting'])
        self.bot.register_message_handler(self.edit_setting, commands=['edit_setting'])
        self.bot.register_message_handler(self.delete_setting, commands=['delete_setting'])
        self.bot.register_message_handler(self.activate_setting, commands=['activate_setting'])
        self.bot.register_message_handler(self.deactivate_setting, commands=['deactivate_setting'])
        self.bot.register_message_handler(self.help_settings, commands=['help_settings'])
        self.bot.register_message_handler(self.menu_settings, commands=['menu_settings'])
        
        # Обработчики callback-запросов для команд
        self.bot.register_callback_query_handler(self.cmd_get_settings_callback, func=lambda call: call.data == 'cmd_get_settings')
        self.bot.register_callback_query_handler(self.cmd_set_setting_callback, func=lambda call: call.data == 'cmd_set_setting')
        self.bot.register_callback_query_handler(self.cmd_update_setting_callback, func=lambda call: call.data == 'cmd_update_setting')
        self.bot.register_callback_query_handler(self.cmd_delete_setting_callback, func=lambda call: call.data == 'cmd_delete_setting')
        self.bot.register_callback_query_handler(self.cmd_activate_setting_callback, func=lambda call: call.data == 'cmd_activate_setting')
        self.bot.register_callback_query_handler(self.cmd_deactivate_setting_callback, func=lambda call: call.data == 'cmd_deactivate_setting')
        self.bot.register_callback_query_handler(self.cmd_help_settings_callback, func=lambda call: call.data == 'cmd_help_settings')
        self.bot.register_callback_query_handler(self.menu_settings_callback, func=lambda call: call.data == 'menu_settings')
    
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
            
            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_settings"
            )
            keyboard.add(back_btn)
            
            if not settings:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['info']} В системе нет настроек уведомлений.",
                    reply_markup=keyboard
                )
                return
            
            # Формируем сообщение со списком настроек
            settings_text = f"{EMOJI['setting']} <b>Список настроек уведомлений ({len(settings)}):</b>\n\n"
            
            for setting_item in settings:
                # Получаем объекты настройки и шаблона
                setting = setting_item['setting']  # Объект NotificationSetting
                template = setting_item['template']  # Объект NotificationTemplate
                
                setting_id = setting.id
                template_id = template.id
                template_name = template.name or 'Неизвестный шаблон'
                days_before = setting.days_before
                time_str = setting.time
                is_active = setting.is_active
                
                status_emoji = EMOJI['active'] if is_active else EMOJI['inactive']
                
                setting_text = (
                    f"{status_emoji} <b>ID {setting_id}</b>\n"
                    f"Шаблон: {template_name} (ID: {template_id})\n"
                    f"Дней до события: {days_before}\n"
                    f"Время отправки: {time_str}\n\n"
                )
                
                settings_text += setting_text
            
            self.send_message(message.chat.id, settings_text, reply_markup=keyboard)
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
                # Текст с инструкцией по добавлению настройки, как в callback-обработчике
                text = (
                    f"{EMOJI['plus']} <b>Добавление настройки уведомления</b>\n\n"
                    f"Для добавления настройки отправьте команду в формате:\n"
                    f"<code>/set_setting [id_шаблона] [дней_до_события] [время_отправки]</code>\n\n"
                    f"Например:\n"
                    f"<code>/set_setting 1 1 12:00</code>\n\n"
                    f"где:\n"
                    f"• id_шаблона - ID шаблона уведомления\n"
                    f"• дней_до_события - за сколько дней до события отправлять\n"
                    f"• время_отправки - время отправки в формате ЧЧ:ММ"
                )
                
                # Создаем клавиатуру с кнопками "Список шаблонов" и "Назад"
                keyboard = types.InlineKeyboardMarkup()
                templates_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['template']} Список шаблонов", 
                    callback_data="cmd_templates_list"
                )
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_settings"
                )
                keyboard.add(templates_btn)
                keyboard.add(back_btn)
                
                self.send_message(message.chat.id, text, reply_markup=keyboard)
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
                # Добавляем кнопку "Назад" к сообщению об успешном создании
                keyboard = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_settings"
                )
                keyboard.add(back_btn)
                
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['success']} Настройка уведомления успешно добавлена.",
                    reply_markup=keyboard
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
    def update_setting(self, message: types.Message) -> None:
        """
        Обработчик команды /update_setting.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            
            if len(args) < 4:
                # Текст с инструкцией по обновлению настройки
                text = (
                    f"{EMOJI['edit']} <b>Обновление настройки уведомления</b>\n\n"
                    f"Для обновления настройки отправьте команду в формате:\n"
                    f"<code>/update_setting [id] [id_шаблона] [дней_до_события] [время_отправки]</code>\n\n"
                    f"Например:\n"
                    f"<code>/update_setting 1 2 3 15:30</code>\n\n"
                    f"где:\n"
                    f"• id - ID настройки\n"
                    f"• id_шаблона - новый ID шаблона уведомления\n"
                    f"• дней_до_события - новое значение дней до события\n"
                    f"• время_отправки - новое время отправки в формате ЧЧ:ММ"
                )
                
                # Создаем клавиатуру с кнопками "Список настроек" и "Назад"
                keyboard = types.InlineKeyboardMarkup()
                list_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['list']} Список настроек", 
                    callback_data="cmd_get_settings"
                )
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_settings"
                )
                keyboard.add(list_btn)
                keyboard.add(back_btn)
                
                self.send_message(message.chat.id, text, reply_markup=keyboard)
                return
            
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
            setting.template_id = template_id
            setting.days_before = days_before
            setting.time = time_str
            
            result = self.setting_service.update_setting(setting)
            
            if result:
                # Добавляем кнопку "Назад" к сообщению об успешном обновлении
                keyboard = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_settings"
                )
                keyboard.add(back_btn)
                
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['success']} Настройка с ID {setting_id} успешно обновлена.",
                    reply_markup=keyboard
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
    def edit_setting(self, message: types.Message) -> None:
        """
        Обработчик команды /edit_setting. Алиас для /update_setting.
        
        Args:
            message: Сообщение от пользователя
        """
        # Делегируем обработку методу update_setting
        self.update_setting(message)
    
    @admin_required
    @log_errors
    def delete_setting(self, message: types.Message) -> None:
        """
        Обработчик команды /delete_setting.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            
            if len(args) < 1:
                # Текст с инструкцией по удалению настройки
                text = (
                    f"{EMOJI['minus']} <b>Удаление настройки уведомления</b>\n\n"
                    f"Для удаления настройки отправьте команду в формате:\n"
                    f"<code>/delete_setting [id]</code>\n\n"
                    f"Например:\n"
                    f"<code>/delete_setting 1</code>\n\n"
                    f"Для получения ID настройки используйте команду /get_settings или нажмите кнопку «Список настроек»."
                )
                
                # Создаем клавиатуру с кнопками "Список настроек" и "Назад"
                keyboard = types.InlineKeyboardMarkup()
                list_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['list']} Список настроек", 
                    callback_data="cmd_get_settings"
                )
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_settings"
                )
                keyboard.add(list_btn)
                keyboard.add(back_btn)
                
                self.send_message(message.chat.id, text, reply_markup=keyboard)
                return
            
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
                # Добавляем кнопку "Назад" к сообщению об успешном удалении
                keyboard = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_settings"
                )
                keyboard.add(back_btn)
                
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['success']} Настройка с ID {setting_id} успешно удалена.",
                    reply_markup=keyboard
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
    def activate_setting(self, message: types.Message) -> None:
        """
        Обработчик команды /activate_setting.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            
            if len(args) < 1:
                # Текст с инструкцией по активации настройки
                text = (
                    f"{EMOJI['check']} <b>Активация настройки уведомления</b>\n\n"
                    f"Для активации настройки отправьте команду в формате:\n"
                    f"<code>/activate_setting [id]</code>\n\n"
                    f"Например:\n"
                    f"<code>/activate_setting 1</code>\n\n"
                    f"Для получения ID настройки используйте команду /get_settings или нажмите кнопку «Список настроек»."
                )
                
                # Создаем клавиатуру с кнопками "Список настроек" и "Назад"
                keyboard = types.InlineKeyboardMarkup()
                list_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['list']} Список настроек", 
                    callback_data="cmd_get_settings"
                )
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_settings"
                )
                keyboard.add(list_btn)
                keyboard.add(back_btn)
                
                self.send_message(message.chat.id, text, reply_markup=keyboard)
                return
            
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
            if setting.is_active:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['info']} Настройка с ID {setting_id} уже активна."
                )
                return
            
            # Активируем настройку
            result = self.setting_service.toggle_setting_active(setting_id, True)
            
            if result:
                # Добавляем кнопку "Назад" к сообщению об успешной активации
                keyboard = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_settings"
                )
                keyboard.add(back_btn)
                
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['success']} Настройка с ID {setting_id} успешно активирована.",
                    reply_markup=keyboard
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
    def deactivate_setting(self, message: types.Message) -> None:
        """
        Обработчик команды /deactivate_setting.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            
            if len(args) < 1:
                # Текст с инструкцией по деактивации настройки
                text = (
                    f"{EMOJI['cross']} <b>Деактивация настройки уведомления</b>\n\n"
                    f"Для деактивации настройки отправьте команду в формате:\n"
                    f"<code>/deactivate_setting [id]</code>\n\n"
                    f"Например:\n"
                    f"<code>/deactivate_setting 1</code>\n\n"
                    f"Для получения ID настройки используйте команду /get_settings или нажмите кнопку «Список настроек»."
                )
                
                # Создаем клавиатуру с кнопками "Список настроек" и "Назад"
                keyboard = types.InlineKeyboardMarkup()
                list_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['list']} Список настроек", 
                    callback_data="cmd_get_settings"
                )
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_settings"
                )
                keyboard.add(list_btn)
                keyboard.add(back_btn)
                
                self.send_message(message.chat.id, text, reply_markup=keyboard)
                return
            
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
            if not setting.is_active:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['info']} Настройка с ID {setting_id} уже неактивна."
                )
                return
            
            # Деактивируем настройку
            result = self.setting_service.toggle_setting_active(setting_id, False)
            
            if result:
                # Добавляем кнопку "Назад" к сообщению об успешной деактивации
                keyboard = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_settings"
                )
                keyboard.add(back_btn)
                
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['success']} Настройка с ID {setting_id} успешно деактивирована.",
                    reply_markup=keyboard
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
        text = self._get_help_text()
        self.send_message(message.chat.id, text, parse_mode='HTML')
        logger.info(f"Отправлена справка по настройкам администратору {message.from_user.id}")
    
    @admin_required
    @log_errors
    def menu_settings(self, message: types.Message) -> None:
        """
        Отображает меню управления настройками уведомлений.
        
        Args:
            message: Сообщение пользователя
        """
        try:
            # Текст с описанием раздела настроек
            text = (
                f"{EMOJI['setting']} <b>Управление настройками уведомлений</b>\n\n"
                f"В этом разделе вы можете управлять настройками уведомлений:\n"
                f"• Просматривать список настроек\n"
                f"• Добавлять новые настройки\n"
                f"• Обновлять существующие настройки\n"
                f"• Удалять настройки\n"
                f"• Активировать/деактивировать настройки\n\n"
                f"Выберите действие:"
            )
            
            # Создаем клавиатуру с кнопками для управления настройками
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            
            # Кнопки для основных действий с настройками
            list_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['list']} Список настроек", 
                callback_data="cmd_get_settings"
            )
            add_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['plus']} Добавить настройку", 
                callback_data="cmd_set_setting"
            )
            update_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['edit']} Изменить настройку", 
                callback_data="cmd_update_setting"
            )
            remove_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['minus']} Удалить настройку", 
                callback_data="cmd_delete_setting"
            )
            
            # Кнопки для активации/деактивации
            activate_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['check']} Активировать", 
                callback_data="cmd_activate_setting"
            )
            deactivate_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['cross']} Деактивировать", 
                callback_data="cmd_deactivate_setting"
            )
            
            # Кнопка справки
            help_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['help']} Справка", 
                callback_data="cmd_help_settings"
            )
            
            # Кнопка возврата в главное меню
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} В главное меню", 
                callback_data="menu_main"
            )
            
            # Добавляем кнопки в клавиатуру
            keyboard.add(list_btn, add_btn)
            keyboard.add(update_btn, remove_btn)
            keyboard.add(activate_btn, deactivate_btn)
            keyboard.add(help_btn)
            keyboard.add(back_btn)
            
            # Отправляем сообщение с клавиатурой
            self.send_message(
                chat_id=message.chat.id,
                text=text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике menu_settings: {str(e)}")
            self.send_message(
                chat_id=message.chat.id,
                text=f"{EMOJI['error']} Произошла ошибка: {str(e)}"
            )
    
    @log_errors
    def menu_settings_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для меню настроек уведомлений.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем права администратора
            if not self.is_admin(call.from_user.id):
                self.answer_callback_query(call.id, "У вас нет прав администратора", show_alert=True)
                return
            
            # Текст с описанием раздела настроек
            text = (
                f"{EMOJI['setting']} <b>Управление настройками уведомлений</b>\n\n"
                f"В этом разделе вы можете управлять настройками уведомлений:\n"
                f"• Просматривать список настроек\n"
                f"• Добавлять новые настройки\n"
                f"• Обновлять существующие настройки\n"
                f"• Удалять настройки\n"
                f"• Активировать/деактивировать настройки\n\n"
                f"Выберите действие:"
            )
            
            # Создаем клавиатуру с кнопками для управления настройками
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            
            # Кнопки для основных действий с настройками
            list_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['list']} Список настроек", 
                callback_data="cmd_get_settings"
            )
            add_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['plus']} Добавить настройку", 
                callback_data="cmd_set_setting"
            )
            update_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['edit']} Изменить настройку", 
                callback_data="cmd_update_setting"
            )
            remove_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['minus']} Удалить настройку", 
                callback_data="cmd_delete_setting"
            )
            
            # Кнопки для активации/деактивации
            activate_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['check']} Активировать", 
                callback_data="cmd_activate_setting"
            )
            deactivate_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['cross']} Деактивировать", 
                callback_data="cmd_deactivate_setting"
            )
            
            # Кнопка справки
            help_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['help']} Справка", 
                callback_data="cmd_help_settings"
            )
            
            # Кнопка возврата в главное меню
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} В главное меню", 
                callback_data="menu_main"
            )
            
            # Добавляем кнопки в клавиатуру
            keyboard.add(list_btn, add_btn)
            keyboard.add(update_btn, remove_btn)
            keyboard.add(activate_btn, deactivate_btn)
            keyboard.add(help_btn)
            keyboard.add(back_btn)
            
            # Обновляем сообщение
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            # Отвечаем на callback-запрос
            self.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике callback-запроса menu_settings: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    def _get_help_text(self) -> str:
        """
        Формирует справочный текст по настройкам уведомлений.
        
        Returns:
            str: Справочный текст
        """
        return (
            f"{EMOJI['help']} <b>Справка по настройкам уведомлений</b>\n\n"
            f"<b>Доступные команды:</b>\n\n"
            f"/get_settings - получить список всех настроек\n"
            f"/set_setting [id_шаблона] [дней_до_события] [время_отправки] - добавить настройку\n"
            f"/update_setting [id] [id_шаблона] [дней_до_события] [время_отправки] - обновить настройку\n"
            f"/delete_setting [id] - удалить настройку\n"
            f"/activate_setting [id] - активировать настройку\n"
            f"/deactivate_setting [id] - деактивировать настройку\n"
            f"/help_settings - показать эту справку\n\n"
            f"<b>Примеры:</b>\n\n"
            f"/set_setting 1 2 15:00 - создать настройку для шаблона #1, за 2 дня до события, отправлять в 15:00\n"
            f"/update_setting 3 2 1 10:30 - обновить настройку #3, установить шаблон #2, за 1 день, время 10:30\n"
            f"/delete_setting 2 - удалить настройку #2\n"
            f"/activate_setting 1 - активировать настройку #1\n"
            f"/deactivate_setting 3 - деактивировать настройку #3"
        )

    # Обработчики callback-запросов
    
    @log_errors
    def cmd_get_settings_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды get_settings.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем права администратора
            if not self.is_admin(call.from_user.id):
                self.answer_callback_query(call.id, "У вас нет прав администратора", show_alert=True)
                return
            
            # Получаем все настройки с информацией о шаблонах
            settings = self.setting_service.get_settings_with_templates()
            
            if not settings:
                text = f"{EMOJI['info']} В системе нет настроек уведомлений."
            else:
                # Формируем сообщение со списком настроек
                text = f"{EMOJI['setting']} <b>Список настроек уведомлений ({len(settings)}):</b>\n\n"
                
                for setting_item in settings:
                    # Получаем объекты настройки и шаблона
                    setting = setting_item['setting']  # Объект NotificationSetting
                    template = setting_item['template']  # Объект NotificationTemplate
                    
                    setting_id = setting.id
                    template_id = template.id
                    template_name = template.name or 'Неизвестный шаблон'
                    days_before = setting.days_before
                    time_str = setting.time
                    is_active = setting.is_active
                    
                    status_emoji = EMOJI['active'] if is_active else EMOJI['inactive']
                    
                    setting_text = (
                        f"{status_emoji} <b>ID {setting_id}</b>\n"
                        f"Шаблон: {template_name} (ID: {template_id})\n"
                        f"Дней до события: {days_before}\n"
                        f"Время отправки: {time_str}\n\n"
                    )
                    
                    text += setting_text
            
            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_settings"
            )
            keyboard.add(back_btn)
            
            # Обновляем сообщение
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            # Отвечаем на callback-запрос
            self.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике callback-запроса cmd_get_settings: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    @log_errors
    def cmd_set_setting_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды set_setting.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем права администратора
            if not self.is_admin(call.from_user.id):
                self.answer_callback_query(call.id, "У вас нет прав администратора", show_alert=True)
                return
            
            # Текст с инструкцией по добавлению настройки
            text = (
                f"{EMOJI['plus']} <b>Добавление настройки уведомления</b>\n\n"
                f"Для добавления настройки отправьте команду в формате:\n"
                f"<code>/set_setting [id_шаблона] [дней_до_события] [время_отправки]</code>\n\n"
                f"Например:\n"
                f"<code>/set_setting 1 1 12:00</code>\n\n"
                f"где:\n"
                f"• id_шаблона - ID шаблона уведомления\n"
                f"• дней_до_события - за сколько дней до события отправлять\n"
                f"• время_отправки - время отправки в формате ЧЧ:ММ"
            )
            
            # Создаем клавиатуру с кнопками "Список шаблонов" и "Назад"
            keyboard = types.InlineKeyboardMarkup()
            templates_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['template']} Список шаблонов", 
                callback_data="cmd_templates_list"
            )
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_settings"
            )
            keyboard.add(templates_btn)
            keyboard.add(back_btn)
            
            # Обновляем сообщение
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            # Отвечаем на callback-запрос
            self.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике callback-запроса cmd_set_setting: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    @log_errors
    def cmd_update_setting_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды update_setting.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем права администратора
            if not self.is_admin(call.from_user.id):
                self.answer_callback_query(call.id, "У вас нет прав администратора", show_alert=True)
                return
            
            # Текст с инструкцией по обновлению настройки
            text = (
                f"{EMOJI['edit']} <b>Обновление настройки уведомления</b>\n\n"
                f"Для обновления настройки отправьте команду в формате:\n"
                f"<code>/update_setting [id] [id_шаблона] [дней_до_события] [время_отправки]</code>\n\n"
                f"Например:\n"
                f"<code>/update_setting 1 2 3 15:30</code>\n\n"
                f"где:\n"
                f"• id - ID настройки\n"
                f"• id_шаблона - новый ID шаблона уведомления\n"
                f"• дней_до_события - новое значение дней до события\n"
                f"• время_отправки - новое время отправки в формате ЧЧ:ММ"
            )
            
            # Создаем клавиатуру с кнопками "Список настроек" и "Назад"
            keyboard = types.InlineKeyboardMarkup()
            list_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['list']} Список настроек", 
                callback_data="cmd_get_settings"
            )
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_settings"
            )
            keyboard.add(list_btn)
            keyboard.add(back_btn)
            
            # Обновляем сообщение
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            # Отвечаем на callback-запрос
            self.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике callback-запроса cmd_update_setting: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    @log_errors
    def cmd_delete_setting_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды delete_setting.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем права администратора
            if not self.is_admin(call.from_user.id):
                self.answer_callback_query(call.id, "У вас нет прав администратора", show_alert=True)
                return
            
            # Текст с инструкцией по удалению настройки
            text = (
                f"{EMOJI['minus']} <b>Удаление настройки уведомления</b>\n\n"
                f"Для удаления настройки отправьте команду в формате:\n"
                f"<code>/delete_setting [id]</code>\n\n"
                f"Например:\n"
                f"<code>/delete_setting 1</code>\n\n"
                f"Для получения ID настройки используйте команду /get_settings или нажмите кнопку «Список настроек»."
            )
            
            # Создаем клавиатуру с кнопками "Список настроек" и "Назад"
            keyboard = types.InlineKeyboardMarkup()
            list_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['list']} Список настроек", 
                callback_data="cmd_get_settings"
            )
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_settings"
            )
            keyboard.add(list_btn)
            keyboard.add(back_btn)
            
            # Обновляем сообщение
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            # Отвечаем на callback-запрос
            self.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике callback-запроса cmd_delete_setting: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    @log_errors
    def cmd_activate_setting_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды activate_setting.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем права администратора
            if not self.is_admin(call.from_user.id):
                self.answer_callback_query(call.id, "У вас нет прав администратора", show_alert=True)
                return
            
            # Текст с инструкцией по активации настройки
            text = (
                f"{EMOJI['check']} <b>Активация настройки уведомления</b>\n\n"
                f"Для активации настройки отправьте команду в формате:\n"
                f"<code>/activate_setting [id]</code>\n\n"
                f"Например:\n"
                f"<code>/activate_setting 1</code>\n\n"
                f"Для получения ID настройки используйте команду /get_settings или нажмите кнопку «Список настроек»."
            )
            
            # Создаем клавиатуру с кнопками "Список настроек" и "Назад"
            keyboard = types.InlineKeyboardMarkup()
            list_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['list']} Список настроек", 
                callback_data="cmd_get_settings"
            )
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_settings"
            )
            keyboard.add(list_btn)
            keyboard.add(back_btn)
            
            # Обновляем сообщение
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            # Отвечаем на callback-запрос
            self.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике callback-запроса cmd_activate_setting: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    @log_errors
    def cmd_deactivate_setting_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды deactivate_setting.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем права администратора
            if not self.is_admin(call.from_user.id):
                self.answer_callback_query(call.id, "У вас нет прав администратора", show_alert=True)
                return
            
            # Текст с инструкцией по деактивации настройки
            text = (
                f"{EMOJI['cross']} <b>Деактивация настройки уведомления</b>\n\n"
                f"Для деактивации настройки отправьте команду в формате:\n"
                f"<code>/deactivate_setting [id]</code>\n\n"
                f"Например:\n"
                f"<code>/deactivate_setting 1</code>\n\n"
                f"Для получения ID настройки используйте команду /get_settings или нажмите кнопку «Список настроек»."
            )
            
            # Создаем клавиатуру с кнопками "Список настроек" и "Назад"
            keyboard = types.InlineKeyboardMarkup()
            list_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['list']} Список настроек", 
                callback_data="cmd_get_settings"
            )
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_settings"
            )
            keyboard.add(list_btn)
            keyboard.add(back_btn)
            
            # Обновляем сообщение
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            # Отвечаем на callback-запрос
            self.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике callback-запроса cmd_deactivate_setting: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    @log_errors
    def cmd_help_settings_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды help_settings.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Справка по настройкам уведомлений
            text = self._get_help_text()
            
            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_settings"
            )
            keyboard.add(back_btn)
            
            # Обновляем сообщение
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            # Отвечаем на callback-запрос
            self.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике callback-запроса cmd_help_settings: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True) 