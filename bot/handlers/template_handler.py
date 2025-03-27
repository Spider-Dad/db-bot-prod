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
from bot.constants import EMOJI, ERROR_MESSAGES, ALLOWED_HTML_TAGS, TEMPLATE_VARIABLES, TEMPLATE_HELP_TEXT
from .base_handler import BaseHandler
from .decorators import admin_required, log_errors, command_args

logger = logging.getLogger(__name__)


class TemplateHandler(BaseHandler):
    """
    Обработчик команд для управления шаблонами уведомлений.
    
    Обрабатывает команды, связанные с созданием, редактированием и удалением
    шаблонов уведомлений.
    """
    
    def __init__(self, bot: telebot.TeleBot, template_service: TemplateService, user_service: UserService):
        """
        Инициализация обработчика шаблонов уведомлений.
        
        Args:
            bot: Экземпляр бота Telegram
            template_service: Сервис для работы с шаблонами уведомлений
            user_service: Сервис для работы с пользователями
        """
        super().__init__(bot)
        self.template_service = template_service
        self.user_service = user_service
        
    def register_handlers(self) -> None:
        """
        Регистрация обработчиков для шаблонов.
        """
        # Регистрация обработчиков команд для шаблонов
        self.bot.register_message_handler(self.get_templates, commands=['get_templates'])
        self.bot.register_message_handler(self.set_template, commands=['set_template'])
        self.bot.register_message_handler(self.update_template, commands=['update_template'])
        self.bot.register_message_handler(self.delete_template, commands=['delete_template'])
        self.bot.register_message_handler(self.preview_template, commands=['preview_template'])
        self.bot.register_message_handler(self.test_template, commands=['test_template'])
        self.bot.register_message_handler(self.activate_template, commands=['activate_template'])
        self.bot.register_message_handler(self.deactivate_template, commands=['deactivate_template'])
        self.bot.register_message_handler(self.help_template, commands=['help_template'])
        self.bot.register_message_handler(self.menu_templates, commands=['menu_templates'])
        
        # Регистрация обработчиков callback-запросов для шаблонов
        self.bot.register_callback_query_handler(self.cmd_add_template_callback, func=lambda call: call.data == 'cmd_add_template')
        self.bot.register_callback_query_handler(self.cmd_remove_template_callback, func=lambda call: call.data == 'cmd_remove_template')
        self.bot.register_callback_query_handler(self.cmd_templates_list_callback, func=lambda call: call.data == 'cmd_templates_list')
        self.bot.register_callback_query_handler(self.cmd_update_template_callback, func=lambda call: call.data == 'cmd_update_template')
        self.bot.register_callback_query_handler(self.cmd_test_template_callback, func=lambda call: call.data == 'cmd_test_template')
        self.bot.register_callback_query_handler(self.cmd_preview_template_callback, func=lambda call: call.data == 'cmd_preview_template')
        self.bot.register_callback_query_handler(self.cmd_activate_template_callback, func=lambda call: call.data == 'cmd_activate_template')
        self.bot.register_callback_query_handler(self.cmd_deactivate_template_callback, func=lambda call: call.data == 'cmd_deactivate_template')
        self.bot.register_callback_query_handler(self.cmd_template_help_callback, func=lambda call: call.data == 'cmd_template_help')
        self.bot.register_callback_query_handler(self.menu_templates_callback, func=lambda call: call.data == 'menu_templates')
    
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
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['info']} В системе нет шаблонов уведомлений."
                )
                return
            
            # Формируем сообщение со списком шаблонов
            templates_text = f"{EMOJI['template']} <b>Список шаблонов уведомлений ({len(templates)}):</b>\n\n"
            
            for template in templates:
                template_id = template.id
                name = template.name
                category = template.category
                text = template.template
                is_active = template.is_active
                
                # Ограничиваем длину текста для отображения
                if len(text) > 50:
                    text = text[:50] + "..."
                
                status_emoji = EMOJI['active'] if is_active else EMOJI['inactive']
                
                template_text = (
                    f"{status_emoji} <b>ID {template_id}: {name}</b>\n"
                    f"Категория: {category}\n"
                    f"Текст: <code>{text}</code>\n\n"
                )
                
                templates_text += template_text
            
            self.send_message(message.chat.id, templates_text)
            logger.info(f"Отправлен список шаблонов администратору {message.from_user.id}")
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка шаблонов: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
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
            args = self.extract_command_args(message.text)
            
            if len(args) < 2:
                self.send_message(
                    message.chat.id, 
                    f"{EMOJI['error']} <b>Ошибка:</b> Неверный формат команды.\n\n"
                    f"Используйте: <code>/set_template [название] [категория] [текст шаблона]</code>\n\n"
                    f"Например: <code>/set_template День_рождения birthdays Завтра день рождения у {{name}}!</code>"
                )
                return
            
            # Извлекаем аргументы
            name = args[0]
            category = args[1] if len(args) > 2 else "general"
            text = args[2] if len(args) > 2 else args[1]
            
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
                valid_vars = ", ".join([f"{{{v}}}" for v in TEMPLATE_VARIABLES])
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
                text=text,
                is_active=True
            )
            
            # Добавляем шаблон в базу
            result = self.template_service.create_template(template)
            
            if result:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['success']} Шаблон \"{name}\" успешно добавлен."
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
    @command_args(2)
    def update_template(self, message: types.Message, args: List[str]) -> None:
        """
        Обработчик команды /update_template.
        
        Args:
            message: Сообщение от пользователя
            args: Аргументы команды
        """
        try:
            # Извлекаем ID шаблона и новый текст
            try:
                template_id = int(args[0])
            except ValueError:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> ID шаблона должен быть числом."
                )
                return
            
            new_text = args[1]
            
            # Получаем шаблон из базы
            template = self.template_service.get_template_by_id(template_id)
            
            if not template:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Шаблон с ID {template_id} не найден."
                )
                return
            
            # Проверяем валидность HTML-тегов
            if not self._validate_html_tags(new_text):
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Шаблон содержит недопустимые HTML-теги.\n\n"
                    f"Разрешены только теги: {', '.join(ALLOWED_HTML_TAGS)}"
                )
                return
            
            # Проверяем валидность переменных шаблона
            if not self._validate_template_variables(new_text):
                valid_vars = ", ".join([f"{{{v}}}" for v in TEMPLATE_VARIABLES])
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Шаблон содержит недопустимые переменные.\n\n"
                    f"Разрешены только переменные: {valid_vars}"
                )
                return
            
            # Обновляем шаблон
            template.template = new_text
            result = self.template_service.update_template(template)
            
            if result:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['success']} Шаблон с ID {template_id} успешно обновлен."
                )
                logger.info(f"Обновлен шаблон с ID {template_id} администратором {message.from_user.id}")
            else:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Не удалось обновить шаблон."
                )
                
        except Exception as e:
            logger.error(f"Ошибка при обновлении шаблона: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    @command_args(1)
    def delete_template(self, message: types.Message, args: List[str]) -> None:
        """
        Обработчик команды /delete_template.
        
        Args:
            message: Сообщение от пользователя
            args: Аргументы команды
        """
        try:
            # Извлекаем ID шаблона
            try:
                template_id = int(args[0])
            except ValueError:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> ID шаблона должен быть числом."
                )
                return
            
            # Получаем шаблон из базы для проверки
            template = self.template_service.get_template_by_id(template_id)
            
            if not template:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Шаблон с ID {template_id} не найден."
                )
                return
            
            # Удаляем шаблон
            result = self.template_service.delete_template(template_id)
            
            if result:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['success']} Шаблон с ID {template_id} успешно удален."
                )
                logger.info(f"Удален шаблон с ID {template_id} администратором {message.from_user.id}")
            else:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Не удалось удалить шаблон."
                )
                
        except Exception as e:
            logger.error(f"Ошибка при удалении шаблона: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
            
    @admin_required
    @log_errors
    @command_args(1)
    def preview_template(self, message: types.Message, args: List[str]) -> None:
        """
        Обработчик команды /preview_template.
        
        Args:
            message: Сообщение от пользователя
            args: Аргументы команды
        """
        try:
            # Извлекаем ID шаблона
            try:
                template_id = int(args[0])
            except ValueError:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> ID шаблона должен быть числом."
                )
                return
            
            # Получаем шаблон из базы
            template = self.template_service.get_template_by_id(template_id)
            
            if not template:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Шаблон с ID {template_id} не найден."
                )
                return
            
            # Формируем пример данных для предпросмотра
            sample_data = {
                'name': 'Иван Иванов',
                'username': 'ivanov',
                'date': '01.01.2025',
                'days_until': 3
            }
            
            # Форматируем шаблон с примером данных
            try:
                formatted_text = self.template_service.format_template(template, sample_data)
                
                # Отправляем предпросмотр
                preview_text = (
                    f"{EMOJI['template']} <b>Предпросмотр шаблона:</b>\n"
                    f"ID: {template_id}\n"
                    f"Название: {template.name}\n"
                    f"Категория: {template.category}\n\n"
                    f"<b>Текст шаблона:</b>\n<code>{template.template}</code>\n\n"
                    f"<b>С примером данных:</b>\n{formatted_text}"
                )
                
                self.send_message(message.chat.id, preview_text)
                logger.info(f"Отправлен предпросмотр шаблона с ID {template_id} администратору {message.from_user.id}")
                
            except Exception as format_error:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка форматирования шаблона:</b> {str(format_error)}"
                )
                
        except Exception as e:
            logger.error(f"Ошибка при предпросмотре шаблона: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    @command_args(2)
    def test_template(self, message: types.Message, args: List[str]) -> None:
        """
        Обработчик команды /test_template.
        
        Args:
            message: Сообщение от пользователя
            args: Аргументы команды
        """
        try:
            # Извлекаем ID шаблона и ID пользователя для теста
            try:
                template_id = int(args[0])
                user_id = int(args[1])
            except ValueError:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> ID шаблона и ID пользователя должны быть числами."
                )
                return
            
            # Получаем шаблон из базы
            template = self.template_service.get_template_by_id(template_id)
            
            if not template:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Шаблон с ID {template_id} не найден."
                )
                return
            
            # Получаем пользователя для теста
            user = self.user_service.get_user_by_telegram_id(user_id)
            
            if not user:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Пользователь с ID {user_id} не найден."
                )
                return
            
            # Формируем данные для шаблона
            template_data = {
                'name': f"{user.first_name} {user.last_name}".strip() if user.last_name else user.first_name,
                'username': user.username or '',
                'date': datetime.now().strftime('%d.%m.%Y'),
                'days_until': 0
            }
            
            # Форматируем шаблон
            try:
                formatted_text = self.template_service.format_template(template, template_data)
                
                # Отправляем тестовое сообщение пользователю
                try:
                    self.send_message(user_id, formatted_text)
                    
                    # Уведомляем администратора
                    self.send_message(
                        message.chat.id,
                        f"{EMOJI['success']} Тестовое сообщение успешно отправлено пользователю с ID {user_id}."
                    )
                    logger.info(f"Отправлено тестовое сообщение с шаблоном ID {template_id} пользователю {user_id}")
                    
                except Exception as send_error:
                    self.send_message(
                        message.chat.id,
                        f"{EMOJI['error']} <b>Ошибка при отправке сообщения:</b> {str(send_error)}"
                    )
                
            except Exception as format_error:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка форматирования шаблона:</b> {str(format_error)}"
                )
                
        except Exception as e:
            logger.error(f"Ошибка при тестировании шаблона: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    @command_args(1)
    def activate_template(self, message: types.Message, args: List[str]) -> None:
        """
        Обработчик команды /activate_template.
        
        Args:
            message: Сообщение от пользователя
            args: Аргументы команды
        """
        try:
            # Извлекаем ID шаблона
            try:
                template_id = int(args[0])
            except ValueError:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> ID шаблона должен быть числом."
                )
                return
            
            # Получаем шаблон из базы для проверки
            template = self.template_service.get_template_by_id(template_id)
            
            if not template:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Шаблон с ID {template_id} не найден."
                )
                return
            
            # Если шаблон уже активен, сообщаем об этом
            if template.is_active:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['info']} Шаблон с ID {template_id} уже активен."
                )
                return
            
            # Активируем шаблон
            result = self.template_service.toggle_template_active(template_id, True)
            
            if result:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['success']} Шаблон с ID {template_id} успешно активирован."
                )
                logger.info(f"Активирован шаблон с ID {template_id} администратором {message.from_user.id}")
            else:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Не удалось активировать шаблон."
                )
                
        except Exception as e:
            logger.error(f"Ошибка при активации шаблона: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    @command_args(1)
    def deactivate_template(self, message: types.Message, args: List[str]) -> None:
        """
        Обработчик команды /deactivate_template.
        
        Args:
            message: Сообщение от пользователя
            args: Аргументы команды
        """
        try:
            # Извлекаем ID шаблона
            try:
                template_id = int(args[0])
            except ValueError:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> ID шаблона должен быть числом."
                )
                return
            
            # Получаем шаблон из базы для проверки
            template = self.template_service.get_template_by_id(template_id)
            
            if not template:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Шаблон с ID {template_id} не найден."
                )
                return
            
            # Если шаблон уже неактивен, сообщаем об этом
            if not template.is_active:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['info']} Шаблон с ID {template_id} уже неактивен."
                )
                return
            
            # Деактивируем шаблон
            result = self.template_service.toggle_template_active(template_id, False)
            
            if result:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['success']} Шаблон с ID {template_id} успешно деактивирован."
                )
                logger.info(f"Деактивирован шаблон с ID {template_id} администратором {message.from_user.id}")
            else:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Не удалось деактивировать шаблон."
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
        self.send_message(message.chat.id, help_text)
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
        
        # Для команд создания и обновления шаблонов, разделяем аргументы особым образом
        if command_text.startswith(('/set_template', '/update_template')):
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
                f"<code>/set_template День_рождения birthday Завтра день рождения у {{name}}!</code>\n\n"
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
        Обработчик callback-запроса для команды templates_list.
        
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
            else:
                # Формируем сообщение со списком шаблонов
                text = f"{EMOJI['template']} <b>Список шаблонов уведомлений ({len(templates)}):</b>\n\n"
                
                for template in templates:
                    template_id = template.id
                    name = template.name
                    category = template.category
                    template_text = template.template
                    is_active = template.is_active
                    
                    # Ограничиваем длину текста для отображения
                    if len(template_text) > 50:
                        template_text = template_text[:50] + "..."
                    
                    status_emoji = EMOJI['active'] if is_active else EMOJI['inactive']
                    
                    template_info = (
                        f"{status_emoji} <b>ID {template_id}: {name}</b>\n"
                        f"Категория: {category}\n"
                        f"Текст: <code>{template_text}</code>\n\n"
                    )
                    
                    text += template_info
            
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
            logger.error(f"Ошибка в обработчике callback-запроса cmd_templates_list: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
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
                f"{EMOJI['edit']} <b>Обновление шаблона</b>\n\n"
                f"Для обновления шаблона отправьте команду в формате:\n"
                f"<code>/update_template [id] [текст шаблона]</code>\n\n"
                f"Например:\n"
                f"<code>/update_template 1 Завтра день рождения у {{name}}!</code>\n\n"
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
    def cmd_test_template_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды test_template.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем права администратора
            if not self.is_admin(call.from_user.id):
                self.answer_callback_query(call.id, "У вас нет прав администратора", show_alert=True)
                return
            
            # Текст с инструкцией по тестированию шаблона
            text = (
                f"{EMOJI['test']} <b>Тестирование шаблона</b>\n\n"
                f"Для тестирования шаблона отправьте команду в формате:\n"
                f"<code>/test_template [id шаблона] [id пользователя]</code>\n\n"
                f"Например:\n"
                f"<code>/test_template 1 123456789</code>\n\n"
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
            logger.error(f"Ошибка в обработчике callback-запроса cmd_test_template: {str(e)}")
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
        import re
        
        # Ищем все переменные в тексте
        var_pattern = re.compile(r'\{([^}]+)\}')
        variables = var_pattern.findall(text)
        
        # Проверяем, что все найденные переменные разрешены
        for var in variables:
            if var not in TEMPLATE_VARIABLES:
                return False
        
        return True
    
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
                f"• Обновлять существующие шаблоны\n"
                f"• Удалять шаблоны\n"
                f"• Активировать/деактивировать шаблоны\n"
                f"• Просматривать и тестировать шаблоны\n\n"
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
                text=f"{EMOJI['eye']} Предпросмотр", 
                callback_data="cmd_preview_template"
            )
            test_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['test']} Тестировать", 
                callback_data="cmd_test_template"
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
            keyboard.add(list_btn, add_btn)
            keyboard.add(update_btn, remove_btn)
            keyboard.add(preview_btn, test_btn)
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
                f"• Обновлять существующие шаблоны\n"
                f"• Удалять шаблоны\n"
                f"• Активировать/деактивировать шаблоны\n"
                f"• Просматривать и тестировать шаблоны\n\n"
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
                text=f"{EMOJI['eye']} Предпросмотр", 
                callback_data="cmd_preview_template"
            )
            test_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['test']} Тестировать", 
                callback_data="cmd_test_template"
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
            keyboard.add(list_btn, add_btn)
            keyboard.add(update_btn, remove_btn)
            keyboard.add(preview_btn, test_btn)
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
            self.send_message(
                chat_id=message.chat.id,
                text=f"{EMOJI['error']} Произошла ошибка: {str(e)}"
            ) 