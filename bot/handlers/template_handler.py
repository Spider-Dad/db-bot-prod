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
        """Регистрация обработчиков команд для управления шаблонами уведомлений."""
        # Команды для работы с шаблонами
        self.bot.message_handler(commands=['get_templates'])(self.get_templates)
        self.bot.message_handler(commands=['set_template'])(self.set_template)
        self.bot.message_handler(commands=['update_template'])(self.update_template)
        self.bot.message_handler(commands=['delete_template'])(self.delete_template)
        self.bot.message_handler(commands=['preview_template'])(self.preview_template)
        self.bot.message_handler(commands=['test_template'])(self.test_template)
        self.bot.message_handler(commands=['activate_template'])(self.activate_template)
        self.bot.message_handler(commands=['deactivate_template'])(self.deactivate_template)
        self.bot.message_handler(commands=['help_template'])(self.help_template)
        
        # Обработчики callback-запросов для команд
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_get_templates')(self.cmd_get_templates_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_set_template')(self.cmd_set_template_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_update_template')(self.cmd_update_template_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_delete_template')(self.cmd_delete_template_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_preview_template')(self.cmd_preview_template_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_test_template')(self.cmd_test_template_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_activate_template')(self.cmd_activate_template_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_deactivate_template')(self.cmd_deactivate_template_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_help_template')(self.cmd_help_template_callback)
    
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
    def cmd_get_templates_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды get_templates.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.get_templates(call.message)
    
    @log_errors
    def cmd_set_template_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды set_template.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.send_message(
            call.message.chat.id,
            f"{EMOJI['info']} Введите команду в формате: <code>/set_template [название] [категория] [текст шаблона]</code>\n\n"
            f"Например: <code>/set_template День_рождения birthdays Завтра день рождения у {{name}}!</code>"
        )
    
    @log_errors
    def cmd_update_template_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды update_template.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.send_message(
            call.message.chat.id,
            f"{EMOJI['info']} Введите команду в формате: <code>/update_template [id] [новый текст шаблона]</code>\n\n"
            f"Например: <code>/update_template 1 Завтра день рождения у {{name}}!</code>"
        )
    
    @log_errors
    def cmd_delete_template_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды delete_template.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.send_message(
            call.message.chat.id,
            f"{EMOJI['info']} Введите команду в формате: <code>/delete_template [id]</code>\n\n"
            f"Например: <code>/delete_template 1</code>"
        )
    
    @log_errors
    def cmd_preview_template_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды preview_template.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.send_message(
            call.message.chat.id,
            f"{EMOJI['info']} Введите команду в формате: <code>/preview_template [id]</code>\n\n"
            f"Например: <code>/preview_template 1</code>"
        )
    
    @log_errors
    def cmd_test_template_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды test_template.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.send_message(
            call.message.chat.id,
            f"{EMOJI['info']} Введите команду в формате: <code>/test_template [id шаблона] [id пользователя]</code>\n\n"
            f"Например: <code>/test_template 1 123456789</code>"
        )
    
    @log_errors
    def cmd_activate_template_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды activate_template.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.send_message(
            call.message.chat.id,
            f"{EMOJI['info']} Введите команду в формате: <code>/activate_template [id]</code>\n\n"
            f"Например: <code>/activate_template 1</code>"
        )
    
    @log_errors
    def cmd_deactivate_template_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды deactivate_template.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.send_message(
            call.message.chat.id,
            f"{EMOJI['info']} Введите команду в формате: <code>/deactivate_template [id]</code>\n\n"
            f"Например: <code>/deactivate_template 1</code>"
        )
    
    @log_errors
    def cmd_help_template_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды help_template.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.help_template(call.message)
    
    def _validate_html_tags(self, text: str) -> bool:
        """
        Проверка валидности HTML-тегов в тексте шаблона.
        
        Args:
            text: Текст шаблона
            
        Returns:
            True, если все HTML-теги в тексте валидны, иначе False
        """
        import re
        
        # Ищем все HTML-теги в тексте
        tag_pattern = re.compile(r'<(\w+)[^>]*>')
        tags = tag_pattern.findall(text)
        
        # Проверяем, что все найденные теги разрешены
        for tag in tags:
            if tag.lower() not in ALLOWED_HTML_TAGS:
                return False
        
        return True
    
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