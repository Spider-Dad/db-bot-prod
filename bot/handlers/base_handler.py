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
    
    def send_message(self, chat_id: int, text: str, parse_mode: str = 'HTML',
                    reply_markup: Optional[Union[telebot.types.InlineKeyboardMarkup, 
                            telebot.types.ReplyKeyboardMarkup, 
                            telebot.types.ReplyKeyboardRemove, 
                            telebot.types.ForceReply]] = None) -> None:
        """
        Отправка сообщения с обработкой ошибок.
        
        Args:
            chat_id: Идентификатор чата
            text: Текст сообщения
            parse_mode: Режим парсинга текста ('HTML', 'Markdown')
            reply_markup: Разметка клавиатуры (опционально)
        """
        try:
            self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения пользователю {chat_id}: {str(e)}")
    
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