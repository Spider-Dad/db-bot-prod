"""
Модели данных для приложения.

Этот модуль содержит определения классов моделей данных, используемых в приложении.
Модели представляют собой типизированные объекты для работы с данными сущностей.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Union


@dataclass
class User:
    """Модель пользователя."""
    
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birth_date: Optional[str] = None
    is_admin: bool = False
    is_subscribed: bool = True
    is_notifications_enabled: bool = True
    created_at: Union[datetime, str] = field(default_factory=lambda: datetime.now())
    updated_at: Union[datetime, str] = field(default_factory=lambda: datetime.now())
    id: Optional[int] = None


@dataclass
class NotificationTemplate:
    """Модель шаблона уведомления."""
    
    name: str
    template: str
    category: str
    is_active: bool = True
    created_at: Union[datetime, str] = field(default_factory=lambda: datetime.now())
    updated_at: Union[datetime, str] = field(default_factory=lambda: datetime.now())
    id: Optional[int] = None


@dataclass
class NotificationSetting:
    """Модель настройки уведомления."""
    
    template_id: int
    days_before: int
    time: str
    is_active: bool = True
    created_at: Union[datetime, str] = field(default_factory=lambda: datetime.now())
    updated_at: Union[datetime, str] = field(default_factory=lambda: datetime.now())
    id: Optional[int] = None
    
    # Дополнительные поля, которые присоединяются при запросе из БД
    template: Optional[NotificationTemplate] = None


class NotificationLog:
    """
    Модель записи журнала уведомлений.
    
    Атрибуты:
        id: ID записи
        user_id: ID пользователя
        message: Текст сообщения
        status: Статус отправки ('success', 'error', 'warning')
        error_message: Сообщение об ошибке (если есть)
        created_at: Дата и время создания записи
    """
    
    def __init__(
        self,
        id: Optional[int] = None,
        user_id: Optional[int] = None,
        message: str = "",
        status: str = "success",
        error_message: Optional[str] = None,
        created_at: Optional[str] = None
    ):
        """
        Инициализация модели записи журнала уведомлений.
        
        Args:
            id: ID записи
            user_id: ID пользователя
            message: Текст сообщения
            status: Статус отправки ('success', 'error', 'warning')
            error_message: Сообщение об ошибке (если есть)
            created_at: Дата и время создания записи
        """
        self.id = id
        self.user_id = user_id
        self.message = message
        self.status = status
        self.error_message = error_message
        self.created_at = created_at 