"""
Пакет репозиториев для работы с базой данных.

Репозитории предоставляют интерфейс для взаимодействия с базой данных
и изолируют бизнес-логику от деталей хранения данных.
"""

from bot.repositories.database_manager import DatabaseManager
from bot.repositories.user_repository import UserRepository
from bot.repositories.template_repository import TemplateRepository
from bot.repositories.notification_setting_repository import NotificationSettingRepository
from bot.repositories.notification_log_repository import NotificationLogRepository

__all__ = [
    'DatabaseManager',
    'UserRepository',
    'TemplateRepository',
    'NotificationSettingRepository',
    'NotificationLogRepository'
] 