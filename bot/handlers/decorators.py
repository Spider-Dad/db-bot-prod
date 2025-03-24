"""
Декораторы для обработчиков бота.

Этот модуль содержит декораторы, которые можно применять к методам-обработчикам
для проверки различных условий перед выполнением основной логики.
"""

import logging
import functools
from typing import Callable, Any, List, Optional

import telebot
from telebot import types

from config import ADMIN_IDS

logger = logging.getLogger(__name__)


def admin_required(func: Callable) -> Callable:
    """
    Декоратор для проверки, является ли пользователь администратором.
    
    Args:
        func: Функция-обработчик
        
    Returns:
        Декорированная функция
    """
    @functools.wraps(func)
    def wrapper(self, message: types.Message, *args, **kwargs) -> Any:
        user_id = message.from_user.id
        
        if user_id not in ADMIN_IDS:
            logger.warning(f"Попытка доступа к административной функции от неадминистратора: {user_id}")
            self.bot.send_message(
                message.chat.id,
                "⚠️ У вас нет прав администратора для выполнения этой команды."
            )
            return None
        
        return func(self, message, *args, **kwargs)
    
    return wrapper


def registered_only(func: Callable) -> Callable:
    """
    Декоратор для проверки, зарегистрирован ли пользователь в системе.
    
    Args:
        func: Функция-обработчик
        
    Returns:
        Декорированная функция
    """
    @functools.wraps(func)
    def wrapper(self, message: types.Message, *args, **kwargs) -> Any:
        user_id = message.from_user.id
        
        # Проверяем, есть ли пользователь в системе
        user = self.user_service.get_user_by_telegram_id(user_id)
        
        if not user:
            logger.warning(f"Попытка доступа к функции от незарегистрированного пользователя: {user_id}")
            self.bot.send_message(
                message.chat.id,
                "⚠️ Вы не зарегистрированы в системе. Используйте /start для регистрации."
            )
            return None
        
        # Передаем найденного пользователя в обработчик
        return func(self, message, user, *args, **kwargs)
    
    return wrapper


def log_errors(func: Callable) -> Callable:
    """
    Декоратор для логирования ошибок в обработчиках.
    
    Args:
        func: Функция-обработчик
        
    Returns:
        Декорированная функция
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs) -> Any:
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            # Получаем информацию о сообщении, если оно есть в аргументах
            message = None
            for arg in args:
                if isinstance(arg, types.Message):
                    message = arg
                    break
            
            user_id = message.from_user.id if message else "Неизвестный пользователь"
            command = message.text if message else "Неизвестная команда"
            
            logger.error(f"Ошибка в обработчике {func.__name__} от пользователя {user_id}: {str(e)}")
            
            # Отправляем сообщение об ошибке пользователю
            if message:
                self.bot.send_message(
                    message.chat.id,
                    "❌ Произошла ошибка при обработке вашего запроса. Администраторы уведомлены."
                )
                
            # Уведомляем администраторов об ошибке
            error_message = f"""<b>⚠️ Ошибка в боте</b>

<b>Пользователь:</b> {user_id}
<b>Команда:</b> {command}
<b>Ошибка:</b> {str(e)}"""

            for admin_id in ADMIN_IDS:
                try:
                    self.bot.send_message(admin_id, error_message, parse_mode='HTML')
                except Exception:
                    pass
            
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