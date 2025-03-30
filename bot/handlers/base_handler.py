"""
Базовый обработчик для Telegram-бота.

Этот модуль содержит базовый класс для всех обработчиков команд и сообщений
Telegram-бота, предоставляя общие функции и интерфейсы.
"""

import logging
import telebot
from typing import Dict, List, Callable, Any, Optional, Union, Set
import re

from bot.core.models import User
from config import ADMIN_IDS
from bot.utils.keyboard_manager import KeyboardManager

logger = logging.getLogger(__name__)


class BaseHandler:
    """
    Базовый класс для всех обработчиков бота.
    
    Предоставляет общие функции и утилиты для обработки сообщений и команд.
    """
    
    def __init__(self, bot: telebot.TeleBot):
        """
        Инициализация базового обработчика.
        
        Args:
            bot: Экземпляр бота Telegram
        """
        self.bot = bot
        self.keyboard_manager = KeyboardManager()
        
    def register_handlers(self) -> None:
        """
        Регистрация обработчиков сообщений и команд.
        
        Переопределяется в дочерних классах для регистрации конкретных обработчиков.
        """
        pass
    
    def is_admin(self, user_id: int) -> bool:
        """
        Проверка, является ли пользователь администратором.
        
        Args:
            user_id: Идентификатор пользователя в Telegram
            
        Returns:
            True, если пользователь является администратором, иначе False
        """
        return user_id in ADMIN_IDS
    
    def is_registered_user(self, user_id: int) -> bool:
        """
        Проверка, зарегистрирован ли пользователь в системе.
        
        Args:
            user_id: Идентификатор пользователя в Telegram
            
        Returns:
            True, если пользователь зарегистрирован, иначе False
        """
        # Администраторы всегда считаются зарегистрированными
        if self.is_admin(user_id):
            return True
        
        # Проверка в базе данных, если у класса есть доступ к сервису пользователей
        if hasattr(self, 'user_service'):
            try:
                user = self.user_service.get_user_by_telegram_id(user_id)
                return user is not None
            except Exception as e:
                logger.error(f"Ошибка при проверке регистрации пользователя: {str(e)}")
        
        return False
    
    def send_message(self, chat_id: int, text: str, parse_mode: str = 'HTML',
                    reply_markup: Optional[Union[telebot.types.InlineKeyboardMarkup, 
                            telebot.types.ReplyKeyboardMarkup, 
                            telebot.types.ReplyKeyboardRemove, 
                            telebot.types.ForceReply]] = None) -> Optional[telebot.types.Message]:
        """
        Отправка сообщения с обработкой ошибок.
        
        Args:
            chat_id: Идентификатор чата
            text: Текст сообщения
            parse_mode: Режим парсинга текста ('HTML', 'Markdown')
            reply_markup: Разметка клавиатуры (опционально)
            
        Returns:
            Optional[telebot.types.Message]: Объект отправленного сообщения или None в случае ошибки
        """
        try:
            return self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения пользователю {chat_id}: {str(e)}")
            return None
    
    def edit_message_text(self, text: str, chat_id: int = None, message_id: int = None, 
                         inline_message_id: str = None, parse_mode: str = 'HTML',
                         reply_markup: Optional[telebot.types.InlineKeyboardMarkup] = None) -> bool:
        """
        Редактирование текста сообщения с обработкой ошибок.
        
        Args:
            text: Новый текст сообщения
            chat_id: Идентификатор чата (опционально)
            message_id: Идентификатор сообщения (опционально)
            inline_message_id: Идентификатор инлайн-сообщения (опционально)
            parse_mode: Режим парсинга текста ('HTML', 'Markdown')
            reply_markup: Разметка клавиатуры (опционально)
            
        Returns:
            bool: True, если редактирование успешно, иначе False
        """
        try:
            self.bot.edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=message_id,
                inline_message_id=inline_message_id,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка редактирования сообщения: {str(e)}")
            return False
    
    def answer_callback_query(self, callback_query_id: str, text: str = None, 
                             show_alert: bool = False, url: str = None, 
                             cache_time: int = 0) -> bool:
        """
        Ответ на callback-запрос с обработкой ошибок.
        
        Args:
            callback_query_id: Идентификатор callback-запроса
            text: Текст уведомления (опционально)
            show_alert: Показывать как оповещение (опционально)
            url: URL для перехода (опционально)
            cache_time: Время кэширования (опционально)
            
        Returns:
            bool: True, если ответ успешен, иначе False
        """
        try:
            self.bot.answer_callback_query(
                callback_query_id=callback_query_id,
                text=text,
                show_alert=show_alert,
                url=url,
                cache_time=cache_time
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка ответа на callback-запрос: {str(e)}")
            return False
    
    def extract_command_args(self, text: str, expected_args_count: Optional[int] = None) -> List[str]:
        """
        Извлечение аргументов команды из текста сообщения.
        
        Args:
            text: Текст сообщения
            expected_args_count: Ожидаемое количество аргументов (опционально)
            
        Returns:
            Список аргументов команды
        """
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            return []
            
        # Извлекаем аргументы из сообщения (все после команды)
        args_text = parts[1].strip()
        
        if expected_args_count and expected_args_count == 1:
            return [args_text]
            
        # Разбиваем на аргументы, учитывая кавычки
        args = []
        current_arg = ""
        in_quotes = False
        quote_char = None
        
        for char in args_text:
            if char in ['"', "'"]:
                if not in_quotes:
                    # Начало цитаты
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    # Конец цитаты
                    in_quotes = False
                    quote_char = None
                else:
                    # Другая кавычка внутри цитаты
                    current_arg += char
            elif char.isspace() and not in_quotes:
                # Пробел вне цитаты - разделитель аргументов
                if current_arg:
                    args.append(current_arg)
                    current_arg = ""
            else:
                current_arg += char
                
        # Добавляем последний аргумент
        if current_arg:
            args.append(current_arg)
            
        return args
    
    def extract_username(self, text: str) -> Optional[str]:
        """
        Извлечение имени пользователя из текста сообщения.
        
        Args:
            text: Текст сообщения
            
        Returns:
            Имя пользователя (без символа @) или None, если не найдено
        """
        # Ищем имя пользователя в формате @username
        match = re.search(r'@([a-zA-Z0-9_]+)', text)
        if match:
            return match.group(1)
        return None
    
    def send_main_menu(self, chat_id: int, is_admin: bool = False, text: str = None) -> None:
        """
        Отправляет главное меню бота.
        
        Args:
            chat_id: Идентификатор чата
            is_admin: Является ли пользователь администратором
            text: Текст сообщения (опционально)
        """
        if not text:
            text = "📋 <b>Главное меню</b>\n\nВыберите действие:"
        
        keyboard = self.keyboard_manager.create_main_menu(is_admin)
        self.send_message(chat_id, text, reply_markup=keyboard)
    
    def update_menu(self, callback_query: telebot.types.CallbackQuery, new_text: str, 
                   new_markup: telebot.types.InlineKeyboardMarkup) -> None:
        """
        Обновляет текущее меню.
        
        Args:
            callback_query: Объект callback-запроса
            new_text: Новый текст сообщения
            new_markup: Новая клавиатура
        """
        try:
            self.bot.edit_message_text(
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                text=new_text,
                reply_markup=new_markup,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Ошибка обновления меню: {str(e)}") 