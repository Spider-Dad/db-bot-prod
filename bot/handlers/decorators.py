"""
Декораторы для обработчиков команд бота.

Этот модуль содержит вспомогательные декораторы для обработчиков команд Telegram-бота,
упрощающие проверку прав доступа и обработку ошибок.
"""

import logging
import functools
from typing import Callable, List, Optional, Any
from telebot import types

from config import ADMIN_IDS
from bot.constants import EMOJI

logger = logging.getLogger(__name__)


def admin_required(func: Callable) -> Callable:
    """
    Декоратор для проверки, является ли пользователь администратором.
    
    Args:
        func: Декорируемая функция
        
    Returns:
        Обертка для функции, проверяющая права администратора
    """
    @functools.wraps(func)
    def wrapper(self, message: types.Message, *args, **kwargs) -> Any:
        user_id = message.from_user.id
        
        # Проверяем, является ли пользователь администратором в конфигурации
        if user_id in ADMIN_IDS:
            return func(self, message, *args, **kwargs)

        # Проверяем, является ли пользователь администратором в базе данных
        try:
            if hasattr(self, 'user_service'):
                user = self.user_service.get_user_by_telegram_id(user_id)
                if user and user.is_admin:
                    return func(self, message, *args, **kwargs)
        except Exception as e:
            logger.error(f"Ошибка при проверке администратора в базе данных: {str(e)}")
            
        # Если пользователь не является администратором
        self.bot.send_message(
            message.chat.id,
            f"{EMOJI['error']} <b>Ошибка:</b> У вас нет прав для выполнения этой команды."
        )
        logger.warning(f"Попытка несанкционированного доступа к admin-команде от пользователя {user_id}")
        return None
        
    return wrapper


def log_errors(func: Callable) -> Callable:
    """
    Декоратор для логирования ошибок при выполнении функции.
    
    Args:
        func: Декорируемая функция
        
    Returns:
        Обертка для функции с логированием ошибок
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs) -> Any:
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            # Получаем имя функции
            func_name = func.__name__
            
            # Логируем ошибку
            logger.error(f"Ошибка в функции {func_name}: {str(e)}", exc_info=True)
            
            # Если это обработчик сообщения, отправляем сообщение об ошибке
            if args and isinstance(args[0], types.Message):
                message = args[0]
                self.bot.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка при выполнении команды:</b> {str(e)}",
                    parse_mode='HTML'
                )
            
            # Продолжаем выполнение, возвращая None
            return None
            
    return wrapper


def command_args(min_args: int = 0, max_args: Optional[int] = None, 
                 usage_message: Optional[str] = None) -> Callable:
    """
    Декоратор для проверки аргументов команды.
    
    Args:
        min_args: Минимальное количество аргументов
        max_args: Максимальное количество аргументов (None - без ограничения)
        usage_message: Сообщение с примером использования команды
        
    Returns:
        Декоратор для функции-обработчика
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, message: types.Message, *args, **kwargs) -> Any:
            command_text = message.text.strip()
            parts = command_text.split(maxsplit=1)
            
            if len(parts) > 1:
                # Извлекаем аргументы из сообщения
                args_text = parts[1].strip()
                command_args = self.extract_command_args(command_text)
            else:
                command_args = []
            
            # Проверяем количество аргументов
            if len(command_args) < min_args:
                logger.warning(f"Недостаточно аргументов: {len(command_args)} < {min_args}")
                self.bot.send_message(
                    message.chat.id,
                    f"⚠️ Недостаточно аргументов. {usage_message if usage_message else ''}"
                )
                return None
            
            if max_args is not None and len(command_args) > max_args:
                logger.warning(f"Слишком много аргументов: {len(command_args)} > {max_args}")
                self.bot.send_message(
                    message.chat.id,
                    f"⚠️ Слишком много аргументов. {usage_message if usage_message else ''}"
                )
                return None
            
            # Передаем аргументы команды в обработчик
            return func(self, message, command_args, *args, **kwargs)
        
        return wrapper
    
    return decorator 