"""
Пакет repositories содержит репозитории для работы с различными сущностями в базе данных.

Репозитории предоставляют интерфейс для выполнения операций CRUD (Create, Read, Update, Delete)
над сущностями, абстрагируя детали взаимодействия с базой данных.
"""

from .user_repository import UserRepository

__all__ = [
    'UserRepository',
] 