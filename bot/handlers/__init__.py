"""
Пакет handlers содержит обработчики команд и сообщений Telegram-бота.

Обработчики отвечают за взаимодействие с пользователями через Telegram API,
используя сервисы для выполнения бизнес-логики.
"""

from .base_handler import BaseHandler
from .common_handlers import CommonHandler
from .decorators import admin_required, registered_only, log_errors, command_args

# Другие обработчики будут добавлены по мере разработки

__all__ = [
    'BaseHandler',
    'CommonHandler',
    'admin_required',
    'registered_only',
    'log_errors',
    'command_args',
] 