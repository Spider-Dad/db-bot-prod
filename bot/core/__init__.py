"""
Пакет core содержит базовые абстракции и интерфейсы для всего приложения.

Этот пакет определяет основную архитектуру приложения и содержит:
- Базовые классы репозиториев для работы с базой данных
- Базовые классы сервисов для бизнес-логики
- Интерфейсы для взаимодействия между компонентами
- Модели данных для всего приложения
"""

from .base_repository import BaseRepository
from .base_service import BaseService
from .interfaces import RepositoryInterface, ServiceInterface, NotificationStrategyInterface
from .models import User, NotificationTemplate, NotificationSetting, NotificationLog

__all__ = [
    'BaseRepository',
    'BaseService',
    'RepositoryInterface',
    'ServiceInterface',
    'NotificationStrategyInterface',
    'User',
    'NotificationTemplate',
    'NotificationSetting',
    'NotificationLog',
] 