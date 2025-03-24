"""
Сервис для работы с пользователями.

Этот модуль содержит сервис, предоставляющий бизнес-логику для операций
с пользователями.
"""

import logging
from typing import List, Dict, Optional, Any

from bot.core.base_service import BaseService
from bot.core.models import User
from bot.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class UserService(BaseService):
    """
    Сервис для работы с пользователями.
    
    Предоставляет бизнес-логику для операций с пользователями,
    используя UserRepository для доступа к данным.
    """
    
    def __init__(self, user_repository: UserRepository):
        """
        Инициализация сервиса пользователей.
        
        Args:
            user_repository: Репозиторий пользователей
        """
        super().__init__()
        self.user_repository = user_repository
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Получение пользователя по ID.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Пользователь или None, если пользователь не найден
        """
        return self.user_repository.get_by_id(user_id)
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        Получение пользователя по Telegram ID.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            Пользователь или None, если пользователь не найден
        """
        return self.user_repository.get_by_telegram_id(telegram_id)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Получение пользователя по имени пользователя.
        
        Args:
            username: Имя пользователя
            
        Returns:
            Пользователь или None, если пользователь не найден
        """
        return self.user_repository.get_by_username(username)
    
    def get_all_users(self) -> List[User]:
        """
        Получение всех пользователей.
        
        Returns:
            Список всех пользователей
        """
        return self.user_repository.get_all()
    
    def get_admin_users(self) -> List[User]:
        """
        Получение всех администраторов.
        
        Returns:
            Список всех администраторов
        """
        return self.user_repository.get_admins()
    
    def get_admin_user_ids(self) -> List[int]:
        """
        Получение Telegram ID всех администраторов.
        
        Returns:
            Список Telegram ID всех администраторов
        """
        return self.user_repository.get_admin_ids()
    
    def create_user(self, user: User) -> int:
        """
        Создание нового пользователя.
        
        Args:
            user: Пользователь для создания
            
        Returns:
            ID созданного пользователя
        """
        return self.user_repository.create(user)
    
    def update_user(self, user_id: int, user: User) -> bool:
        """
        Обновление пользователя.
        
        Args:
            user_id: ID пользователя
            user: Обновленный пользователь
            
        Returns:
            True, если обновление прошло успешно, иначе False
        """
        return self.user_repository.update(user_id, user)
    
    def delete_user(self, user_id: int) -> bool:
        """
        Удаление пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True, если удаление прошло успешно, иначе False
        """
        return self.user_repository.delete(user_id)
    
    def set_admin_status(self, user_id: int, is_admin: bool) -> bool:
        """
        Изменение статуса администратора.
        
        Args:
            user_id: ID пользователя
            is_admin: True - назначить администратором, False - отозвать права администратора
            
        Returns:
            True, если изменение прошло успешно, иначе False
        """
        return self.user_repository.toggle_admin(user_id, is_admin)
    
    def toggle_notifications(self, user_id: int, is_enabled: bool) -> bool:
        """
        Включение/отключение уведомлений.
        
        Args:
            user_id: ID пользователя
            is_enabled: True - включить уведомления, False - отключить уведомления
            
        Returns:
            True, если изменение прошло успешно, иначе False
        """
        return self.user_repository.toggle_notifications(user_id, is_enabled)
    
    def get_users_with_birthdays(self, days_before: int) -> List[User]:
        """
        Получение пользователей, у которых скоро день рождения.
        
        Args:
            days_before: Количество дней до дня рождения
            
        Returns:
            Список пользователей, у которых скоро день рождения
        """
        return self.user_repository.get_users_with_birthdays(days_before)
    
    def execute(self, *args, **kwargs) -> Any:
        """
        Выполнение основной бизнес-логики сервиса.
        
        Этот метод является заглушкой для соответствия интерфейсу BaseService.
        
        Args:
            *args: Позиционные аргументы
            **kwargs: Именованные аргументы
            
        Returns:
            Результат выполнения бизнес-логики
        """
        # Заглушка для соответствия интерфейсу BaseService
        return None 