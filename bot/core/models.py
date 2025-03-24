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


@dataclass
class NotificationLog:
    """Модель лога уведомлений."""
    
    user_id: int
    message: str
    status: str
    error_message: Optional[str] = None
    created_at: Union[datetime, str] = field(default_factory=lambda: datetime.now())
    id: Optional[int] = None 