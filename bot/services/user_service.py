"""
Сервис для работы с пользователями.

Этот модуль содержит сервис, предоставляющий бизнес-логику для операций
с пользователями.
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import date, datetime, timedelta

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
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        Получение пользователя по Telegram ID.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            Пользователь или None, если пользователь не найден
        """
        return self.user_repository.get_user_by_telegram_id(telegram_id)
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Получение пользователя по ID пользователя в базе данных.
        
        Args:
            user_id: ID пользователя в базе данных
            
        Returns:
            Пользователь или None, если пользователь не найден
        """
        return self.user_repository.get_by_id(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Получение пользователя по имени пользователя (username).
        
        Args:
            username: Имя пользователя
            
        Returns:
            Пользователь или None, если пользователь не найден
        """
        return self.user_repository.get_user_by_username(username)
    
    def get_all_users(self) -> List[User]:
        """
        Получение всех пользователей.
        
        Returns:
            Список всех пользователей
        """
        return self.user_repository.get_all_users()
    
    def create_user(self, user: User) -> int:
        """
        Создание нового пользователя.
        
        Args:
            user: Пользователь для создания
            
        Returns:
            ID созданного пользователя или None в случае ошибки
        """
        return self.user_repository.add_user(user)
    
    def update_user(self, user: User) -> bool:
        """
        Обновление пользователя.
        
        Args:
            user: Обновленный пользователь
            
        Returns:
            True, если обновление прошло успешно, иначе False
        """
        return self.user_repository.update_user(user)
    
    def delete_user(self, telegram_id: int) -> bool:
        """
        Удаление пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            True, если удаление прошло успешно, иначе False
        """
        return self.user_repository.delete_user(telegram_id)
    
    def set_admin_status(self, telegram_id: int, is_admin: bool) -> bool:
        """
        Изменение статуса администратора.
        
        Args:
            telegram_id: Telegram ID пользователя
            is_admin: True - назначить администратором, False - отозвать права администратора
            
        Returns:
            True, если изменение прошло успешно, иначе False
        """
        if is_admin:
            return self.user_repository.promote_to_admin(telegram_id)
        else:
            return self.user_repository.demote_from_admin(telegram_id)
    
    def toggle_notifications(self, telegram_id: int, is_enabled: bool) -> bool:
        """
        Включение/отключение уведомлений.
        
        Args:
            telegram_id: Telegram ID пользователя
            is_enabled: True - включить уведомления, False - отключить уведомления
            
        Returns:
            True, если изменение прошло успешно, иначе False
        """
        return self.user_repository.update_user_notifications(telegram_id, is_enabled)
    
    def toggle_subscription(self, telegram_id: int, is_subscribed: bool) -> bool:
        """
        Изменение статуса подписки.
        
        Args:
            telegram_id: Telegram ID пользователя
            is_subscribed: True - подписать пользователя, False - отписать пользователя
            
        Returns:
            True, если изменение прошло успешно, иначе False
        """
        return self.user_repository.update_user_subscription(telegram_id, is_subscribed)
    
    def get_upcoming_birthdays(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """
        Получение ближайших дней рождения.
        
        Args:
            days_ahead: Количество дней вперед для поиска
            
        Returns:
            Список словарей с информацией о пользователях и их днях рождения
        """
        return self.user_repository.get_upcoming_birthdays(days_ahead)
    
    def get_users_with_upcoming_birthdays(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """
        Получение пользователей с ближайшими днями рождения (алиас для get_upcoming_birthdays).
        
        Args:
            days_ahead: Количество дней вперед для поиска
            
        Returns:
            Список словарей с информацией о пользователях и их днях рождения
        """
        return self.get_upcoming_birthdays(days_ahead)
    
    def get_users_with_birthdays_between(self, start_date: date, end_date: date) -> List[User]:
        """
        Получение пользователей, у которых день рождения в указанном диапазоне дат.
        
        Args:
            start_date: Начальная дата диапазона
            end_date: Конечная дата диапазона
            
        Returns:
            Список пользователей с днями рождения в указанном диапазоне
        """
        return self.user_repository.get_users_with_birthdays_between(start_date, end_date)
    
    def get_users_with_birthdays_today(self) -> List[User]:
        """
        Получение пользователей, у которых сегодня день рождения.
        
        Returns:
            Список пользователей с днем рождения сегодня
        """
        today = datetime.now().date()
        return self.user_repository.get_users_with_birthdays_between(today, today)
    
    def get_admin_telegram_ids(self) -> List[int]:
        """
        Получение Telegram ID всех администраторов.
        
        Returns:
            Список Telegram ID всех администраторов
        """
        admin_users = [user for user in self.get_all_users() if user.is_admin]
        return [user.telegram_id for user in admin_users]
    
    def get_all_users_with_birthdays(self) -> List[Dict[str, Any]]:
        """
        Получение всех пользователей с днями рождения, сгруппированных по месяцам.
        
        Returns:
            Список словарей с информацией о пользователях и их днях рождения,
            отсортированный по месяцам и дням
        """
        try:
            # Получаем всех пользователей
            users = self.user_repository.get_all_users()
            
            # Фильтруем пользователей, у которых указана дата рождения
            users_with_birthdays = [user for user in users if user.birth_date]
            
            # Преобразуем в формат, удобный для отображения
            birthdays_list = []
            
            for user in users_with_birthdays:
                try:
                    birth_date_obj = datetime.strptime(user.birth_date, "%Y-%m-%d").date()
                    
                    birthdays_list.append({
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'birth_date': user.birth_date,
                        'month': birth_date_obj.month,
                        'day': birth_date_obj.day
                    })
                except ValueError as ve:
                    logger.warning(f"Неверный формат даты рождения для пользователя {user.id}: {str(ve)}")
            
            # Сортируем по месяцам и дням
            birthdays_list.sort(key=lambda x: (x['month'], x['day']))
            
            return birthdays_list
        
        except Exception as e:
            logger.error(f"Ошибка получения всех пользователей с днями рождения: {str(e)}")
            return []
    
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