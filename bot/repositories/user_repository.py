"""
Репозиторий для работы с пользователями.

Этот модуль содержит репозиторий, отвечающий за операции CRUD с пользователями
в базе данных.
"""

import logging
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime

from bot.core.base_repository import BaseRepository
from bot.core.models import User

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository):
    """
    Репозиторий для работы с пользователями.
    
    Предоставляет методы для создания, чтения, обновления и удаления
    пользователей в базе данных.
    """
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Получение пользователя по ID.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Пользователь или None, если пользователь не найден
        """
        query = "SELECT * FROM users WHERE id = ?"
        result = self.execute_query(query, (user_id,), fetchone=True)
        
        if result:
            return self.to_entity(result)
        return None
    
    def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        Получение пользователя по Telegram ID.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            Пользователь или None, если пользователь не найден
        """
        query = "SELECT * FROM users WHERE telegram_id = ?"
        result = self.execute_query(query, (telegram_id,), fetchone=True)
        
        if result:
            return self.to_entity(result)
        return None
    
    def get_by_username(self, username: str) -> Optional[User]:
        """
        Получение пользователя по имени пользователя.
        
        Args:
            username: Имя пользователя
            
        Returns:
            Пользователь или None, если пользователь не найден
        """
        query = "SELECT * FROM users WHERE username = ?"
        result = self.execute_query(query, (username,), fetchone=True)
        
        if result:
            return self.to_entity(result)
        return None
    
    def get_all(self) -> List[User]:
        """
        Получение всех пользователей.
        
        Returns:
            Список всех пользователей
        """
        query = "SELECT * FROM users ORDER BY id"
        results = self.execute_query(query)
        
        return [self.to_entity(user) for user in results]
    
    def get_admins(self) -> List[User]:
        """
        Получение всех администраторов.
        
        Returns:
            Список всех администраторов
        """
        query = "SELECT * FROM users WHERE is_admin = 1 ORDER BY id"
        results = self.execute_query(query)
        
        return [self.to_entity(user) for user in results]
    
    def get_admin_ids(self) -> List[int]:
        """
        Получение Telegram ID всех администраторов.
        
        Returns:
            Список Telegram ID всех администраторов
        """
        query = "SELECT telegram_id FROM users WHERE is_admin = 1"
        results = self.execute_query(query)
        
        return [user['telegram_id'] for user in results]
    
    def get_subscribed_users(self) -> List[User]:
        """
        Получение всех подписанных пользователей.
        
        Returns:
            Список всех подписанных пользователей
        """
        query = "SELECT * FROM users WHERE is_subscribed = 1 ORDER BY id"
        results = self.execute_query(query)
        
        return [self.to_entity(user) for user in results]
    
    def get_users_with_birthdays(self, days_before: int) -> List[User]:
        """
        Получение пользователей, у которых скоро день рождения.
        
        Args:
            days_before: Количество дней до дня рождения
            
        Returns:
            Список пользователей, у которых скоро день рождения
        """
        query = """
        SELECT * FROM users
        WHERE 
            birth_date IS NOT NULL
            AND (
                strftime('%m-%d', birth_date) = strftime('%m-%d', 'now', '+' || ? || ' days')
            )
        """
        results = self.execute_query(query, (days_before,))
        
        return [self.to_entity(user) for user in results]
    
    def create(self, user: User) -> int:
        """
        Создание нового пользователя.
        
        Args:
            user: Пользователь для создания
            
        Returns:
            ID созданного пользователя
        """
        query = """
        INSERT INTO users (
            telegram_id, username, first_name, last_name, birth_date,
            is_admin, is_subscribed, is_notifications_enabled, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """
        
        data = self.to_db_dict(user)
        
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, (
                    data['telegram_id'],
                    data['username'],
                    data['first_name'],
                    data['last_name'],
                    data['birth_date'],
                    1 if data['is_admin'] else 0,
                    1 if data['is_subscribed'] else 0,
                    1 if data['is_notifications_enabled'] else 0
                ))
                
                # Получаем ID созданного пользователя
                user_id = cursor.lastrowid
                
                return user_id
        except Exception as e:
            logger.error(f"Ошибка создания пользователя: {str(e)}")
            raise
    
    def update(self, user_id: int, user: User) -> bool:
        """
        Обновление пользователя.
        
        Args:
            user_id: ID пользователя
            user: Обновленный пользователь
            
        Returns:
            True, если обновление прошло успешно, иначе False
        """
        query = """
        UPDATE users SET
            username = ?,
            first_name = ?,
            last_name = ?,
            birth_date = ?,
            is_admin = ?,
            is_subscribed = ?,
            is_notifications_enabled = ?,
            updated_at = datetime('now')
        WHERE id = ?
        """
        
        data = self.to_db_dict(user)
        
        try:
            rows_affected = self.execute_update(query, (
                data['username'],
                data['first_name'],
                data['last_name'],
                data['birth_date'],
                1 if data['is_admin'] else 0,
                1 if data['is_subscribed'] else 0,
                1 if data['is_notifications_enabled'] else 0,
                user_id
            ))
            
            return rows_affected > 0
        except Exception as e:
            logger.error(f"Ошибка обновления пользователя: {str(e)}")
            raise
    
    def delete(self, user_id: int) -> bool:
        """
        Удаление пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True, если удаление прошло успешно, иначе False
        """
        query = "DELETE FROM users WHERE id = ?"
        
        try:
            rows_affected = self.execute_update(query, (user_id,))
            
            return rows_affected > 0
        except Exception as e:
            logger.error(f"Ошибка удаления пользователя: {str(e)}")
            raise
    
    def toggle_admin(self, user_id: int, is_admin: bool) -> bool:
        """
        Изменение статуса администратора.
        
        Args:
            user_id: ID пользователя
            is_admin: True - назначить администратором, False - отозвать права администратора
            
        Returns:
            True, если изменение прошло успешно, иначе False
        """
        query = "UPDATE users SET is_admin = ?, updated_at = datetime('now') WHERE id = ?"
        
        try:
            rows_affected = self.execute_update(query, (1 if is_admin else 0, user_id))
            
            return rows_affected > 0
        except Exception as e:
            logger.error(f"Ошибка изменения статуса администратора: {str(e)}")
            raise
    
    def toggle_notifications(self, user_id: int, is_enabled: bool) -> bool:
        """
        Включение/отключение уведомлений.
        
        Args:
            user_id: ID пользователя
            is_enabled: True - включить уведомления, False - отключить уведомления
            
        Returns:
            True, если изменение прошло успешно, иначе False
        """
        query = "UPDATE users SET is_notifications_enabled = ?, updated_at = datetime('now') WHERE id = ?"
        
        try:
            rows_affected = self.execute_update(query, (1 if is_enabled else 0, user_id))
            
            return rows_affected > 0
        except Exception as e:
            logger.error(f"Ошибка изменения статуса уведомлений: {str(e)}")
            raise
    
    def to_entity(self, data: Dict[str, Any]) -> User:
        """
        Преобразование данных из базы данных в объект User.
        
        Args:
            data: Данные из базы данных
            
        Returns:
            Объект User
        """
        return User(
            id=data['id'],
            telegram_id=data['telegram_id'],
            username=data['username'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            birth_date=data['birth_date'],
            is_admin=bool(data['is_admin']),
            is_subscribed=bool(data['is_subscribed']),
            is_notifications_enabled=bool(data['is_notifications_enabled']),
            created_at=data['created_at'],
            updated_at=data['updated_at']
        )
    
    def to_db_dict(self, user: User) -> Dict[str, Any]:
        """
        Преобразование объекта User в словарь для сохранения в базе данных.
        
        Args:
            user: Объект User
            
        Returns:
            Словарь с данными пользователя
        """
        return {
            'id': user.id,
            'telegram_id': user.telegram_id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'birth_date': user.birth_date,
            'is_admin': user.is_admin,
            'is_subscribed': user.is_subscribed,
            'is_notifications_enabled': user.is_notifications_enabled,
            'created_at': user.created_at,
            'updated_at': user.updated_at
        } 