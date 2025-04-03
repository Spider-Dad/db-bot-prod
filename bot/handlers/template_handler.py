"""
Обработчики команд для управления шаблонами уведомлений.

Этот модуль содержит обработчики для команд бота,
связанных с созданием, редактированием и удалением шаблонов уведомлений.
"""

import logging
import telebot
from telebot import types
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from bot.core.models import NotificationTemplate
from bot.services.template_service import TemplateService
from bot.services.user_service import UserService
from bot.constants import EMOJI, ERROR_MESSAGES, ALLOWED_HTML_TAGS, TEMPLATE_VARIABLES, TEMPLATE_HELP_TEXT, SAMPLE_TEMPLATE_DATA
from .base_handler import BaseHandler
from .decorators import admin_required, log_errors, command_args

logger = logging.getLogger(__name__)


class TemplateHandler(BaseHandler):
    """
    Обработчик команд для управления шаблонами уведомлений.
    
    Обрабатывает команды, связанные с созданием, редактированием и удалением
    шаблонов уведомлений.
    """
    
    def __init__(self, bot: telebot.TeleBot, template_service: TemplateService, user_service: UserService, setting_service):
        """
        Инициализация обработчика шаблонов уведомлений.
        
        Args:
            bot: Экземпляр бота Telegram
            template_service: Сервис для работы с шаблонами уведомлений
            user_service: Сервис для работы с пользователями
            setting_service: Сервис для работы с настройками уведомлений
        """
        super().__init__(bot)
        self.template_service = template_service
        self.user_service = user_service
        self.setting_service = setting_service
        
    def register_handlers(self) -> None:
        """Регистрация обработчиков."""
        # Команды для работы с шаблонами
        self.bot.register_message_handler(self.get_templates, commands=['get_templates'])
        self.bot.register_message_handler(self.set_template, commands=['set_template'])
        self.bot.register_message_handler(self.update_template, commands=['update_template'])
        self.bot.register_message_handler(self.delete_template, commands=['delete_template'])
        self.bot.register_message_handler(self.preview_template, commands=['preview_template'])
        self.bot.register_message_handler(self.activate_template, commands=['activate_template'])
        self.bot.register_message_handler(self.deactivate_template, commands=['deactivate_template'])
        self.bot.register_message_handler(self.help_template, commands=['help_template'])
        self.bot.register_message_handler(self.menu_templates, commands=['menu_templates'])
        
        # Callback-обработчики для кнопок в меню
        self.bot.register_callback_query_handler(self.menu_templates_callback, func=lambda call: call.data == 'menu_templates')
        self.bot.register_callback_query_handler(self.cmd_templates_list_callback, func=lambda call: call.data == 'cmd_templates_list')
        self.bot.register_callback_query_handler(self.cmd_add_template_callback, func=lambda call: call.data == 'cmd_add_template')
        self.bot.register_callback_query_handler(self.cmd_update_template_callback, func=lambda call: call.data == 'cmd_update_template')
        self.bot.register_callback_query_handler(self.cmd_remove_template_callback, func=lambda call: call.data == 'cmd_remove_template')
        self.bot.register_callback_query_handler(self.cmd_preview_template_callback, func=lambda call: call.data == 'cmd_preview_template' or call.data.startswith('cmd_preview_template:'))
        self.bot.register_callback_query_handler(self.cmd_activate_template_callback, func=lambda call: call.data == 'cmd_activate_template')
        self.bot.register_callback_query_handler(self.cmd_deactivate_template_callback, func=lambda call: call.data == 'cmd_deactivate_template')
        self.bot.register_callback_query_handler(self.cmd_template_help_callback, func=lambda call: call.data == 'cmd_template_help')
    
    @admin_required
    @log_errors
    def get_templates(self, message: types.Message) -> None:
        """
        Обработчик команды /get_templates.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            # Получаем все шаблоны
            templates = self.template_service.get_all_templates()
            
            if not templates:
                # Создаем клавиатуру с кнопкой "Назад"
                keyboard = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_templates"
                )
                keyboard.add(back_btn)
                
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['info']} В системе нет шаблонов уведомлений.",
                    reply_markup=keyboard
                )
                return
            
            # Для каждого шаблона отправляем отдельное сообщение с полной информацией
            for i, template in enumerate(templates):
                # Используем метод _format_template_info для единообразного форматирования шаблонов
                template_text = self._format_template_info(template)
                
                # Отправляем информацию о шаблоне
                # Если это последний шаблон, добавляем кнопки "Предпросмотр" и "Назад"
                if i == len(templates) - 1:
                    keyboard = types.InlineKeyboardMarkup()
                    preview_btn = types.InlineKeyboardButton(
                        text=f"{EMOJI['eye']} Предпросмотр", 
                        callback_data=f"cmd_preview_template:{template.id}"
                    )
                    back_btn = types.InlineKeyboardButton(
                        text=f"{EMOJI['back']} Назад", 
                        callback_data="menu_templates"
                    )
                    keyboard.add(preview_btn)
                    keyboard.add(back_btn)
                    self.send_message(message.chat.id, template_text, reply_markup=keyboard)
                else:
                    # Для не последних шаблонов добавляем только кнопку "Предпросмотр"
                    keyboard = types.InlineKeyboardMarkup()
                    preview_btn = types.InlineKeyboardButton(
                        text=f"{EMOJI['eye']} Предпросмотр", 
                        callback_data=f"cmd_preview_template:{template.id}"
                    )
                    keyboard.add(preview_btn)
                    self.send_message(message.chat.id, template_text, reply_markup=keyboard)
            
            logger.info(f"Отправлен список шаблонов администратору {message.from_user.id}")
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка шаблонов: {str(e)}")
            
            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_templates"
            )
            keyboard.add(back_btn)
            
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}",
                reply_markup=keyboard
            )
    
    @admin_required
    @log_errors
    def set_template(self, message: types.Message) -> None:
        """
        Обработчик команды /set_template.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            # Разделяем текст на части: команда, название, категория и текст
            parts = message.text.split(' ', 3)
            
            if len(parts) < 4:
                # Если команда вызвана без аргументов, показываем инструкцию и кнопку назад
                # (как в callback-обработчике cmd_add_template_callback)
                
                # Текст с инструкцией по добавлению шаблона
                text = (
                    f"{EMOJI['plus']} <b>Добавление шаблона</b>\n\n"
                    f"Для добавления шаблона отправьте команду в формате:\n"
                    f"<code>/set_template [название] [категория] [текст шаблона]</code>\n\n"
                    f"Например:\n"
                    f"<code>/set_template День_рождения birthday Коллега, привет!🍾 \n📅 Уже скоро {{name}} {{date}} отмечает День Рождения! 🎂 \n Если хочешь принять участие в поздравительном конверте, прошу перевести взнос по номеру телефона <b>{{phone_pay}}</b> на Альфу или Тинькофф до конца дня {{date_before}}. Получатель: <b>{{name_pay}}</b>. \n ⚠️ Пожалуйста, не переводи деньги в другие банки, даже если приложение будет предлагать варианты. \n В комментарии перевода укажи: ДР {{first_name}}</code>\n\n"
                    f"Доступные переменные:\n"
                    f"• {{name}} - Полное имя пользователя\n"
                    f"• {{first_name}} - Имя пользователя\n"
                    f"• {{last_name}} - Фамилия пользователя\n"
                    f"• {{date}} - Дата события\n"
                    f"• {{date_before}} - Дата за день до события\n"
                    f"• {{days_until}} - Количество дней до события\n"
                    f"• {{phone_pay}} - Номер телефона для перевода\n"
                    f"• {{name_pay}} - ФИО получателя платежа"
                )
                
                # Создаем клавиатуру с кнопкой "Назад"
                keyboard = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_templates"
                )
                keyboard.add(back_btn)
                
                self.send_message(message.chat.id, text, reply_markup=keyboard)
                return
            
            # Извлекаем аргументы
            name = parts[1]
            category = parts[2]
            text = parts[3]
            
            # Проверяем валидность HTML-тегов
            if not self._validate_html_tags(text):
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Шаблон содержит недопустимые HTML-теги.\n\n"
                    f"Разрешены только теги: {', '.join(ALLOWED_HTML_TAGS)}"
                )
                return
            
            # Проверяем валидность переменных шаблона
            if not self._validate_template_variables(text):
                # Получаем список допустимых переменных без фигурных скобок для отображения
                allowed_vars = [var.strip('{}') for var in TEMPLATE_VARIABLES]
                valid_vars = ", ".join(["{" + v + "}" for v in allowed_vars])
                
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Шаблон содержит недопустимые переменные.\n\n"
                    f"Разрешены только переменные: {valid_vars}"
                )
                return
            
            # Создаем шаблон
            template = NotificationTemplate(
                name=name,
                category=category,
                template=text,
                is_active=True
            )
            
            # Добавляем шаблон в базу
            result = self.template_service.create_template(template)
            
            if result:
                # Добавляем кнопку "Назад" в сообщение об успешном создании шаблона
                keyboard = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_templates"
                )
                keyboard.add(back_btn)
                
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['success']} Шаблон \"{name}\" успешно добавлен.",
                    reply_markup=keyboard
                )
                logger.info(f"Добавлен шаблон \"{name}\" администратором {message.from_user.id}")
            else:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Не удалось добавить шаблон."
                )
                
        except Exception as e:
            logger.error(f"Ошибка при добавлении шаблона: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    def update_template(self, message: types.Message) -> None:
        """
        Обработчик команды /update_template.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            # Разбираем аргументы команды
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            
            if len(args) < 4:
                # Если команда вызвана без аргументов, показываем инструкцию
                text = (
                    f"{EMOJI['info']} <b>Изменение шаблона</b>\n\n"
                    f"Для изменения шаблона отправьте команду в формате:\n"
                    f"<code>/update_template [id_шаблона] [название] [категория] [текст_шаблона]</code>\n\n"
                    f"Например:\n"
                    f"<code>/update_template 1 День_рождения birthday Новый текст шаблона</code>"
                )
                
                # Создаем клавиатуру с кнопкой "Назад"
                keyboard = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_templates"
                )
                keyboard.add(back_btn)
                
                self.send_message(message.chat.id, text, reply_markup=keyboard)
                return
            
            # Извлекаем аргументы
            try:
                template_id = int(args[0])
            except ValueError:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> ID шаблона должен быть числом."
                )
                return
            
            name = args[1]
            category = args[2]
            text = ' '.join(args[3:])
            
            # Проверяем валидность HTML-тегов
            if not self._validate_html_tags(text):
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> В тексте шаблона содержатся недопустимые HTML-теги."
                )
                return
            
            # Проверяем валидность переменных шаблона
            if not self._validate_template_variables(text):
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> В тексте шаблона содержатся недопустимые переменные."
                )
                return
            
            # Обновляем шаблон
            if self.template_service.update_template(template_id, name, category, text):
                # Создаем клавиатуру с кнопкой "Назад"
                keyboard = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_templates"
                )
                keyboard.add(back_btn)
                
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['success']} Шаблон успешно обновлен.",
                    reply_markup=keyboard
                )
                logger.info(f"Шаблон {template_id} обновлен администратором {message.from_user.id}")
            else:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Шаблон не найден."
                )
                
        except Exception as e:
            logger.error(f"Ошибка при обновлении шаблона: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    def delete_template(self, message: types.Message) -> None:
        """
        Обработчик команды /delete_template.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            # Разбираем аргументы команды
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            
            if len(args) < 1:
                # Если команда вызвана без аргументов, показываем инструкцию
                text = (
                    f"{EMOJI['info']} <b>Удаление шаблона</b>\n\n"
                    f"Для удаления шаблона отправьте команду в формате:\n"
                    f"<code>/delete_template [id_шаблона]</code>\n\n"
                    f"Например:\n"
                    f"<code>/delete_template 1</code>"
                )
                
                # Создаем клавиатуру с кнопкой "Назад"
                keyboard = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_templates"
                )
                keyboard.add(back_btn)
                
                self.send_message(message.chat.id, text, reply_markup=keyboard)
                return
            
            # Извлекаем ID шаблона
            try:
                template_id = int(args[0])
            except ValueError:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> ID шаблона должен быть числом."
                )
                return
            
            # Удаляем шаблон, передавая setting_service для проверки использования шаблона
            if self.template_service.delete_template(template_id, setting_service=self.setting_service):
                # Создаем клавиатуру с кнопкой "Назад"
                keyboard = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_templates"
                )
                keyboard.add(back_btn)
                
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['success']} Шаблон успешно удален.",
                    reply_markup=keyboard
                )
                logger.info(f"Шаблон {template_id} удален администратором {message.from_user.id}")
            else:
                # Получаем настройки шаблона для проверки причины ошибки
                settings = self.setting_service.get_settings_by_template_id(template_id)
                
                if settings:
                    # Если настройки существуют, выводим специальное сообщение
                    error_message = (
                        f"{EMOJI['error']} <b>Ошибка:</b> Невозможно удалить шаблон, т.к. он используется в настройках уведомлений.\n\n"
                        f"Сначала удалите или измените следующие настройки:\n"
                    )
                    
                    # Добавляем первые 3 настройки в сообщение (чтобы не перегружать)
                    for i, setting in enumerate(settings[:3]):
                        error_message += f"• Настройка ID: {setting.id}, время: {setting.time}, дней до события: {setting.days_before}\n"
                    
                    if len(settings) > 3:
                        error_message += f"...и еще {len(settings) - 3} настроек.\n"
                    
                    # Создаем клавиатуру с кнопкой "Настройки" и "Назад"
                    keyboard = types.InlineKeyboardMarkup()
                    settings_btn = types.InlineKeyboardButton(
                        text=f"{EMOJI['setting']} Перейти к настройкам", 
                        callback_data="menu_settings"
                    )
                    back_btn = types.InlineKeyboardButton(
                        text=f"{EMOJI['back']} Назад", 
                        callback_data="menu_templates"
                    )
                    keyboard.add(settings_btn)
                    keyboard.add(back_btn)
                    
                    self.send_message(
                        message.chat.id,
                        error_message,
                        reply_markup=keyboard
                    )
                else:
                    self.send_message(
                        message.chat.id,
                        f"{EMOJI['error']} <b>Ошибка:</b> Шаблон не найден."
                    )
                
        except Exception as e:
            logger.error(f"Ошибка при удалении шаблона: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    def _format_preview_template(self, template_id: int) -> Tuple[str, bool]:
        """
        Форматирует предпросмотр шаблона с тестовыми данными.
        
        Args:
            template_id: ID шаблона
            
        Returns:
            Tuple[str, bool]: Форматированный текст предпросмотра и флаг успеха
        """
        # Получаем шаблон из базы
        template = self.template_service.get_template_by_id(template_id)
        
        if not template:
            return f"{EMOJI['error']} <b>Ошибка:</b> Шаблон с ID {template_id} не найден.", False
        
        # Используем тестовые данные из константы SAMPLE_TEMPLATE_DATA
        
        # Форматируем шаблон с примером данных
        try:
            formatted_text = self.template_service.format_template(template, SAMPLE_TEMPLATE_DATA)
            
            # Формируем предпросмотр
            preview_text = (
                f"{EMOJI['template']} <b>Предпросмотр шаблона:</b>\n"
                f"ID: {template_id}\n"
                f"Название: {template.name}\n"
                f"Категория: {template.category}\n\n"
                f"<b>Текст шаблона:</b>\n{template.template}\n\n"
                f"<b>С примером данных:</b>\n{formatted_text}"
            )
            
            return preview_text, True
            
        except Exception as format_error:
            error_text = f"{EMOJI['error']} <b>Ошибка форматирования шаблона:</b> {str(format_error)}"
            return error_text, False
    
    @admin_required
    @log_errors
    def preview_template(self, message: types.Message) -> None:
        """
        Обработчик команды /preview_template.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            # Разделяем текст на части: команда и id
            parts = message.text.split(' ', 1)
            
            # Проверяем наличие аргументов
            if len(parts) < 2:
                # Создаем клавиатуру с кнопками "Список шаблонов" и "Назад"
                keyboard = types.InlineKeyboardMarkup()
                list_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['list']} Список шаблонов", 
                    callback_data="cmd_templates_list"
                )
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_templates"
                )
                keyboard.add(list_btn)
                keyboard.add(back_btn)
                
                # Отправляем информационное сообщение
                self.send_message(
                    message.chat.id, 
                    f"{EMOJI['eye']} <b>Предпросмотр шаблона</b>\n\n"
                    f"Для предпросмотра шаблона отправьте команду в формате:\n"
                    f"<code>/preview_template [id]</code>\n\n"
                    f"Например:\n"
                    f"<code>/preview_template 1</code>\n\n"
                    f"Чтобы узнать ID шаблона, используйте команду /get_templates или нажмите кнопку «Список шаблонов».",
                    reply_markup=keyboard
                )
                return
            
            # Извлекаем ID шаблона
            try:
                template_id = int(parts[1])
            except ValueError:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> ID шаблона должен быть числом."
                )
                return
            
            # Используем общий метод для форматирования предпросмотра
            preview_text, success = self._format_preview_template(template_id)
            
            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_templates"
            )
            keyboard.add(back_btn)
            
            # Отправляем предпросмотр или сообщение об ошибке
            self.send_message(message.chat.id, preview_text, reply_markup=keyboard)
            
            if success:
                logger.info(f"Отправлен предпросмотр шаблона с ID {template_id} администратору {message.from_user.id}")
                
        except Exception as e:
            logger.error(f"Ошибка при предпросмотре шаблона: {str(e)}")
            
            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_templates"
            )
            keyboard.add(back_btn)
            
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}",
                reply_markup=keyboard
            )
    
    @admin_required
    @log_errors
    def activate_template(self, message: types.Message) -> None:
        """
        Обработчик команды /activate_template.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            # Разбираем аргументы команды
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            
            if len(args) < 1:
                # Если команда вызвана без аргументов, показываем инструкцию
                text = (
                    f"{EMOJI['info']} <b>Активация шаблона</b>\n\n"
                    f"Для активации шаблона отправьте команду в формате:\n"
                    f"<code>/activate_template [id_шаблона]</code>\n\n"
                    f"Например:\n"
                    f"<code>/activate_template 1</code>"
                )
                
                # Создаем клавиатуру с кнопкой "Назад"
                keyboard = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_templates"
                )
                keyboard.add(back_btn)
                
                self.send_message(message.chat.id, text, reply_markup=keyboard)
                return
            
            # Извлекаем ID шаблона
            try:
                template_id = int(args[0])
            except ValueError:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> ID шаблона должен быть числом."
                )
                return
            
            # Активируем шаблон
            if self.template_service.activate_template(template_id):
                # Создаем клавиатуру с кнопкой "Назад"
                keyboard = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_templates"
                )
                keyboard.add(back_btn)
                
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['success']} Шаблон успешно активирован.",
                    reply_markup=keyboard
                )
                logger.info(f"Шаблон {template_id} активирован администратором {message.from_user.id}")
            else:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Шаблон не найден или уже активирован."
                )
                
        except Exception as e:
            logger.error(f"Ошибка при активации шаблона: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    def deactivate_template(self, message: types.Message) -> None:
        """
        Обработчик команды /deactivate_template.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            # Разбираем аргументы команды
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            
            if len(args) < 1:
                # Если команда вызвана без аргументов, показываем инструкцию
                text = (
                    f"{EMOJI['info']} <b>Деактивация шаблона</b>\n\n"
                    f"Для деактивации шаблона отправьте команду в формате:\n"
                    f"<code>/deactivate_template [id_шаблона]</code>\n\n"
                    f"Например:\n"
                    f"<code>/deactivate_template 1</code>"
                )
                
                # Создаем клавиатуру с кнопкой "Назад"
                keyboard = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_templates"
                )
                keyboard.add(back_btn)
                
                self.send_message(message.chat.id, text, reply_markup=keyboard)
                return
            
            # Извлекаем ID шаблона
            try:
                template_id = int(args[0])
            except ValueError:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> ID шаблона должен быть числом."
                )
                return
            
            # Деактивируем шаблон
            if self.template_service.deactivate_template(template_id):
                # Создаем клавиатуру с кнопкой "Назад"
                keyboard = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_templates"
                )
                keyboard.add(back_btn)
                
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['success']} Шаблон успешно деактивирован.",
                    reply_markup=keyboard
                )
                logger.info(f"Шаблон {template_id} деактивирован администратором {message.from_user.id}")
            else:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Шаблон не найден или уже деактивирован."
                )
                
        except Exception as e:
            logger.error(f"Ошибка при деактивации шаблона: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    def help_template(self, message: types.Message) -> None:
        """
        Обработчик команды /help_template.
        
        Args:
            message: Сообщение от пользователя
        """
        help_text = TEMPLATE_HELP_TEXT
        
        # Создаем клавиатуру с кнопкой "Назад"
        keyboard = types.InlineKeyboardMarkup()
        back_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['back']} Назад", 
            callback_data="menu_templates"
        )
        keyboard.add(back_btn)
        
        self.send_message(message.chat.id, help_text, reply_markup=keyboard)
        logger.info(f"Отправлена справка по шаблонам администратору {message.from_user.id}")
    
    def extract_command_args(self, command_text: str) -> List[str]:
        """
        Извлекает аргументы из команды.
        
        Args:
            command_text: Текст команды
            
        Returns:
            Список аргументов команды
        """
        # Разделяем команду на части по пробелу, пропускаем первую часть (саму команду)
        parts = command_text.split(' ', 1)
        if len(parts) < 2:
            return []
        
        args_text = parts[1].strip()
        
        # Если нет аргументов после команды, возвращаем пустой список
        if not args_text:
            return []
        
        # Для команды set_template разделяем аргументы особым образом
        if command_text.startswith('/set_template'):
            args = []
            # Максимум 3 аргумента: имя, категория и текст
            parts = args_text.split(' ', 2)
            for part in parts:
                if part:
                    args.append(part)
            return args
        
        # Для остальных команд просто разделяем по пробелу
        return [arg for arg in args_text.split(' ') if arg]
    
    # Обработчики callback-запросов
    
    @log_errors
    def cmd_add_template_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды add_template.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем права администратора
            if not self.is_admin(call.from_user.id):
                self.answer_callback_query(call.id, "У вас нет прав администратора", show_alert=True)
                return
            
            # Текст с инструкцией по добавлению шаблона
            text = (
                f"{EMOJI['plus']} <b>Добавление шаблона</b>\n\n"
                f"Для добавления шаблона отправьте команду в формате:\n"
                f"<code>/set_template [название] [категория] [текст шаблона]</code>\n\n"
                f"Например:\n"
                f"<code>/set_template День_рождения birthday Коллега, привет!🍾 \n📅 Уже скоро {{name}} {{date}} отмечает День Рождения! 🎂 \n Если хочешь принять участие в поздравительном конверте, прошу перевести взнос по номеру телефона <b>{{phone_pay}}</b> на Альфу или Тинькофф до конца дня {{date_before}}. Получатель: <b>{{name_pay}}</b>. \n ⚠️ Пожалуйста, не переводи деньги в другие банки, даже если приложение будет предлагать варианты. \n В комментарии перевода укажи: ДР {{first_name}}</code>\n\n"
                f"Доступные переменные:\n"
                f"• {{name}} - Полное имя пользователя\n"
                f"• {{first_name}} - Имя пользователя\n"
                f"• {{last_name}} - Фамилия пользователя\n"
                f"• {{date}} - Дата события\n"
                f"• {{date_before}} - Дата за день до события\n"
                f"• {{days_until}} - Количество дней до события\n"
                f"• {{phone_pay}} - Номер телефона для перевода\n"
                f"• {{name_pay}} - ФИО получателя платежа"
            )
            
            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_templates"
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
            logger.error(f"Ошибка в обработчике callback-запроса cmd_add_template: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    @log_errors
    def cmd_remove_template_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды remove_template.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем права администратора
            if not self.is_admin(call.from_user.id):
                self.answer_callback_query(call.id, "У вас нет прав администратора", show_alert=True)
                return
            
            # Текст с инструкцией по удалению шаблона
            text = (
                f"{EMOJI['minus']} <b>Удаление шаблона</b>\n\n"
                f"Для удаления шаблона отправьте команду в формате:\n"
                f"<code>/delete_template [id]</code>\n\n"
                f"Например:\n"
                f"<code>/delete_template 1</code>\n\n"
                f"Чтобы узнать ID шаблона, используйте команду /get_templates или нажмите кнопку «Список шаблонов»."
            )
            
            # Создаем клавиатуру с кнопками "Список шаблонов" и "Назад"
            keyboard = types.InlineKeyboardMarkup()
            list_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['list']} Список шаблонов", 
                callback_data="cmd_templates_list"
            )
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_templates"
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
            logger.error(f"Ошибка в обработчике callback-запроса cmd_remove_template: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    @log_errors
    def cmd_templates_list_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для получения списка шаблонов.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем права администратора
            if not self.is_admin(call.from_user.id):
                self.answer_callback_query(call.id, "У вас нет прав администратора", show_alert=True)
                return
            
            # Получаем все шаблоны
            templates = self.template_service.get_all_templates()
            
            if not templates:
                text = f"{EMOJI['info']} В системе нет шаблонов уведомлений."
                
                # Создаем клавиатуру с кнопкой "Назад"
                keyboard = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_templates"
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
                return
            
            # Отвечаем на callback-запрос
            self.answer_callback_query(call.id, "Получение списка шаблонов")
            
            # Если у нас только один шаблон, показываем его с кнопками "Предпросмотр" и "Назад"
            if len(templates) == 1:
                template = templates[0]
                template_text = self._format_template_info(template)
                
                # Клавиатура с кнопками "Предпросмотр" и "Назад"
                keyboard = types.InlineKeyboardMarkup()
                preview_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['eye']} Предпросмотр", 
                    callback_data=f"cmd_preview_template:{template.id}"
                )
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_templates"
                )
                keyboard.add(preview_btn)
                keyboard.add(back_btn)
                
                # Редактируем текущее сообщение с первым шаблоном и кнопками
                self.bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=template_text,
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
            else:
                # Редактируем текущее сообщение с первым шаблоном и кнопкой "Предпросмотр"
                first_template = templates[0]
                first_template_text = self._format_template_info(first_template)
                
                # Клавиатура с кнопкой "Предпросмотр"
                keyboard_first = types.InlineKeyboardMarkup()
                preview_btn_first = types.InlineKeyboardButton(
                    text=f"{EMOJI['eye']} Предпросмотр", 
                    callback_data=f"cmd_preview_template:{first_template.id}"
                )
                keyboard_first.add(preview_btn_first)
                
                self.bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=first_template_text,
                    reply_markup=keyboard_first,
                    parse_mode='HTML'
                )
                
                # Отправляем промежуточные шаблоны с кнопкой "Предпросмотр"
                for template in templates[1:-1]:
                    template_text = self._format_template_info(template)
                    
                    # Клавиатура с кнопкой "Предпросмотр"
                    keyboard = types.InlineKeyboardMarkup()
                    preview_btn = types.InlineKeyboardButton(
                        text=f"{EMOJI['eye']} Предпросмотр", 
                        callback_data=f"cmd_preview_template:{template.id}"
                    )
                    keyboard.add(preview_btn)
                    
                    self.send_message(call.message.chat.id, template_text, reply_markup=keyboard)
                
                # Отправляем последний шаблон с кнопками "Предпросмотр" и "Назад"
                last_template = templates[-1]
                last_template_text = self._format_template_info(last_template)
                
                # Клавиатура с кнопками "Предпросмотр" и "Назад"
                keyboard_last = types.InlineKeyboardMarkup()
                preview_btn_last = types.InlineKeyboardButton(
                    text=f"{EMOJI['eye']} Предпросмотр", 
                    callback_data=f"cmd_preview_template:{last_template.id}"
                )
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_templates"
                )
                keyboard_last.add(preview_btn_last)
                keyboard_last.add(back_btn)
                
                self.send_message(
                    call.message.chat.id, 
                    last_template_text, 
                    reply_markup=keyboard_last
                )
            
            logger.info(f"Отправлен список шаблонов администратору {call.from_user.id}")
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка шаблонов: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    def _format_template_info(self, template) -> str:
        """
        Форматирует информацию о шаблоне для отображения.
        
        Args:
            template: Объект шаблона
            
        Returns:
            Отформатированная строка с информацией о шаблоне
        """
        template_id = template.id
        name = template.name
        category = template.category
        text = template.template
        is_active = template.is_active
        created_at = template.created_at
        
        # Форматируем дату создания
        try:
            if isinstance(created_at, str):
                created_at_obj = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                created_at_str = created_at_obj.strftime("%Y-%m-%d %H:%M:%S")
            else:
                created_at_str = created_at.strftime("%Y-%m-%d %H:%M:%S")
        except:
            created_at_str = str(created_at)
        
        # Статус шаблона
        status_emoji = "✅" if is_active else "❌"
        status_text = "Активен" if is_active else "Неактивен"
        
        # Получаем настройки уведомлений для данного шаблона, если есть
        notification_settings = self.setting_service.get_settings_by_template_id(template_id)
        
        # Формируем сообщение с полной информацией о шаблоне
        template_text = f"📋 <b>Шаблон #{template_id}</b>\n"
        template_text += f"📝 <b>Название:</b> {name}\n"
        template_text += f"📂 <b>Категория:</b> {category}\n"
        template_text += f"⏱ <b>Создан:</b> {created_at_str}\n"
        template_text += f"📊 <b>Статус:</b> {status_emoji} {status_text}\n\n"
        
        # Добавляем информацию о настройках уведомлений
        template_text += f"⚙️ <b>Настройки уведомлений:</b>\n"
        if notification_settings:
            for setting in notification_settings:
                setting_id = setting.id if hasattr(setting, 'id') else 'N/A'
                days_before = setting.days_before if hasattr(setting, 'days_before') else 0
                time = setting.time if hasattr(setting, 'time') else '12:00'
                is_setting_active = setting.is_active if hasattr(setting, 'is_active') else False
                setting_status = "✅" if is_setting_active else "❌"
                setting_status_text = "Активна" if is_setting_active else "Неактивна"
                
                template_text += f"• id настройки #{setting_id}: За {days_before} дней в {time} - {setting_status} {setting_status_text}\n"
        else:
            template_text += f"• ❌ настройки уведомлений для шаблона отсутствуют\n"
        
        template_text += f"\n🔤 <b>Текст шаблона:</b>\n\n{text}\n"
        
        return template_text
    
    @log_errors
    def cmd_update_template_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды update_template.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем права администратора
            if not self.is_admin(call.from_user.id):
                self.answer_callback_query(call.id, "У вас нет прав администратора", show_alert=True)
                return
            
            # Текст с инструкцией по обновлению шаблона
            text = (
                f"{EMOJI['edit']} <b>Изменение шаблона</b>\n\n"
                f"Для изменения шаблона отправьте команду в формате:\n"
                f"<code>/update_template [id] [текст шаблона]</code>\n\n"
                f"Например:\n"
                f"<code>/update_template 1 Новый текст шаблона </code>\n\n"
                f"Чтобы узнать ID шаблона, используйте команду /get_templates или нажмите кнопку «Список шаблонов»."
            )
            
            # Создаем клавиатуру с кнопками "Список шаблонов" и "Назад"
            keyboard = types.InlineKeyboardMarkup()
            list_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['list']} Список шаблонов", 
                callback_data="cmd_templates_list"
            )
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_templates"
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
            logger.error(f"Ошибка в обработчике callback-запроса cmd_update_template: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    @log_errors
    def cmd_preview_template_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды preview_template.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем права администратора
            if not self.is_admin(call.from_user.id):
                self.answer_callback_query(call.id, "У вас нет прав администратора", show_alert=True)
                return
            
            # Извлекаем ID шаблона из данных callback, если они есть
            callback_data = call.data.split(':')
            if len(callback_data) > 1:
                try:
                    template_id = int(callback_data[1])
                    
                    # Используем общий метод для форматирования предпросмотра
                    preview_text, success = self._format_preview_template(template_id)
                    
                    # Создаем клавиатуру с кнопкой "Назад"
                    keyboard = types.InlineKeyboardMarkup()
                    back_btn = types.InlineKeyboardButton(
                        text=f"{EMOJI['back']} Назад", 
                        callback_data="menu_templates"
                    )
                    keyboard.add(back_btn)
                    
                    # Обновляем сообщение с предпросмотром
                    self.bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=preview_text,
                        reply_markup=keyboard,
                        parse_mode='HTML'
                    )
                    
                    # Отвечаем на callback-запрос
                    self.answer_callback_query(call.id)
                    return
                except ValueError:
                    pass
            
            # Если ID шаблона не получен, показываем форму для ввода ID
            # Текст с инструкцией по предпросмотру шаблона
            text = (
                f"{EMOJI['eye']} <b>Предпросмотр шаблона</b>\n\n"
                f"Для предпросмотра шаблона отправьте команду в формате:\n"
                f"<code>/preview_template [id]</code>\n\n"
                f"Например:\n"
                f"<code>/preview_template 1</code>\n\n"
                f"Чтобы узнать ID шаблона, используйте команду /get_templates или нажмите кнопку «Список шаблонов»."
            )
            
            # Создаем клавиатуру с кнопками "Список шаблонов" и "Назад"
            keyboard = types.InlineKeyboardMarkup()
            list_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['list']} Список шаблонов", 
                callback_data="cmd_templates_list"
            )
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_templates"
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
            logger.error(f"Ошибка в обработчике callback-запроса cmd_preview_template: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    @log_errors
    def cmd_activate_template_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды activate_template.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем права администратора
            if not self.is_admin(call.from_user.id):
                self.answer_callback_query(call.id, "У вас нет прав администратора", show_alert=True)
                return
            
            # Текст с инструкцией по активации шаблона
            text = (
                f"{EMOJI['check']} <b>Активация шаблона</b>\n\n"
                f"Для активации шаблона отправьте команду в формате:\n"
                f"<code>/activate_template [id]</code>\n\n"
                f"Например:\n"
                f"<code>/activate_template 1</code>\n\n"
                f"Чтобы узнать ID шаблона, используйте команду /get_templates или нажмите кнопку «Список шаблонов»."
            )
            
            # Создаем клавиатуру с кнопками "Список шаблонов" и "Назад"
            keyboard = types.InlineKeyboardMarkup()
            list_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['list']} Список шаблонов", 
                callback_data="cmd_templates_list"
            )
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_templates"
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
            logger.error(f"Ошибка в обработчике callback-запроса cmd_activate_template: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    @log_errors
    def cmd_deactivate_template_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды deactivate_template.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем права администратора
            if not self.is_admin(call.from_user.id):
                self.answer_callback_query(call.id, "У вас нет прав администратора", show_alert=True)
                return
            
            # Текст с инструкцией по деактивации шаблона
            text = (
                f"{EMOJI['cross']} <b>Деактивация шаблона</b>\n\n"
                f"Для деактивации шаблона отправьте команду в формате:\n"
                f"<code>/deactivate_template [id]</code>\n\n"
                f"Например:\n"
                f"<code>/deactivate_template 1</code>\n\n"
                f"Чтобы узнать ID шаблона, используйте команду /get_templates или нажмите кнопку «Список шаблонов»."
            )
            
            # Создаем клавиатуру с кнопками "Список шаблонов" и "Назад"
            keyboard = types.InlineKeyboardMarkup()
            list_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['list']} Список шаблонов", 
                callback_data="cmd_templates_list"
            )
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_templates"
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
            logger.error(f"Ошибка в обработчике callback-запроса cmd_deactivate_template: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    @log_errors
    def cmd_template_help_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды template_help.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Отправляем справку по шаблонам
            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_templates"
            )
            keyboard.add(back_btn)
            
            # Обновляем сообщение
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=TEMPLATE_HELP_TEXT,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            # Отвечаем на callback-запрос
            self.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике callback-запроса cmd_template_help: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    def _validate_html_tags(self, text: str) -> bool:
        """
        Проверка валидности HTML-тегов в тексте шаблона.
        
        Args:
            text: Текст шаблона
            
        Returns:
            True, если все HTML-теги в тексте валидны, иначе False
        """
        from bot.utils.validators import validate_html
        
        # Используем функцию validate_html из модуля validators
        is_valid, _ = validate_html(text)
        return is_valid
    
    def _validate_template_variables(self, text: str) -> bool:
        """
        Проверка валидности переменных в тексте шаблона.
        
        Args:
            text: Текст шаблона
            
        Returns:
            True, если все переменные в тексте валидны, иначе False
        """
        from bot.utils.validators import validate_template_variables
        
        # Используем функцию validate_template_variables из модуля validators
        is_valid, _ = validate_template_variables(text)
        return is_valid
    
    @log_errors
    def menu_templates_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для меню шаблонов.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем права администратора
            if not self.is_admin(call.from_user.id):
                self.answer_callback_query(call.id, "У вас нет прав администратора", show_alert=True)
                return
            
            # Текст с описанием раздела шаблонов
            text = (
                f"{EMOJI['template']} <b>Управление шаблонами уведомлений</b>\n\n"
                f"В этом разделе вы можете управлять шаблонами уведомлений:\n"
                f"• Просматривать список шаблонов\n"
                f"• Добавлять новые шаблоны\n"
                f"• Редактировать существующие шаблоны\n"
                f"• Удалять шаблоны\n"
                f"• Активировать/деактивировать шаблоны\n"
                f"• Просматривать шаблоны\n\n"
                f"Выберите действие:"
            )
            
            # Создаем клавиатуру с кнопками для управления шаблонами
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            
            # Кнопки для основных действий с шаблонами
            list_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['list']} Список шаблонов", 
                callback_data="cmd_templates_list"
            )
            add_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['plus']} Добавить шаблон", 
                callback_data="cmd_add_template"
            )
            update_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['edit']} Изменить шаблон", 
                callback_data="cmd_update_template"
            )
            remove_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['minus']} Удалить шаблон", 
                callback_data="cmd_remove_template"
            )
            
            # Кнопки для дополнительных действий
            preview_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['eye']} Предпросмотр шаблона", 
                callback_data="cmd_preview_template"
            )
            activate_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['check']} Активировать", 
                callback_data="cmd_activate_template"
            )
            deactivate_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['cross']} Деактивировать", 
                callback_data="cmd_deactivate_template"
            )
            
            # Кнопка справки
            help_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['help']} Справка", 
                callback_data="cmd_template_help"
            )
            
            # Кнопка возврата в главное меню
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} В главное меню", 
                callback_data="menu_main"
            )
            
            # Добавляем кнопки в клавиатуру
            keyboard.add(list_btn)
            keyboard.add(add_btn, remove_btn)
            keyboard.add(update_btn, preview_btn)
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
            logger.error(f"Ошибка в обработчике callback-запроса menu_templates: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    @admin_required
    @log_errors
    def menu_templates(self, message: types.Message) -> None:
        """
        Отображает меню управления шаблонами.
        
        Args:
            message: Сообщение пользователя
        """
        try:
            # Текст с описанием раздела шаблонов
            text = (
                f"{EMOJI['template']} <b>Управление шаблонами уведомлений</b>\n\n"
                f"В этом разделе вы можете управлять шаблонами уведомлений:\n"
                f"• Просматривать список шаблонов\n"
                f"• Добавлять новые шаблоны\n"
                f"• Редактировать существующие шаблоны\n"
                f"• Удалять шаблоны\n"
                f"• Активировать/деактивировать шаблоны\n"
                f"• Просматривать шаблоны\n\n"
                f"Выберите действие:"
            )
            
            # Создаем клавиатуру с кнопками для управления шаблонами
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            
            # Кнопки для основных действий с шаблонами
            list_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['list']} Список шаблонов", 
                callback_data="cmd_templates_list"
            )
            add_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['plus']} Добавить шаблон", 
                callback_data="cmd_add_template"
            )
            update_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['edit']} Изменить шаблон", 
                callback_data="cmd_update_template"
            )
            remove_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['minus']} Удалить шаблон", 
                callback_data="cmd_remove_template"
            )
            
            # Кнопки для дополнительных действий
            preview_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['eye']} Предпросмотр шаблона", 
                callback_data="cmd_preview_template"
            )
            activate_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['check']} Активировать", 
                callback_data="cmd_activate_template"
            )
            deactivate_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['cross']} Деактивировать", 
                callback_data="cmd_deactivate_template"
            )
            
            # Кнопка справки
            help_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['help']} Справка", 
                callback_data="cmd_template_help"
            )
            
            # Кнопка возврата в главное меню
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} В главное меню", 
                callback_data="menu_main"
            )
            
            # Добавляем кнопки в клавиатуру
            keyboard.add(list_btn)
            keyboard.add(add_btn, remove_btn)
            keyboard.add(update_btn, preview_btn)
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
            logger.error(f"Ошибка в обработчике menu_templates: {str(e)}")
            
            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} В главное меню", 
                callback_data="menu_main"
            )
            keyboard.add(back_btn)
            
            self.send_message(
                chat_id=message.chat.id,
                text=f"{EMOJI['error']} Произошла ошибка: {str(e)}",
                reply_markup=keyboard
            ) 