"""
Базовый класс для репозиториев.

Этот модуль содержит базовый класс для всех репозиториев, который обеспечивает
общую функциональность для работы с базой данных SQLite.
"""

import sqlite3
import logging
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, TypeVar, Generic, Tuple, Union
from abc import ABC, abstractmethod

from .interfaces import RepositoryInterface

T = TypeVar('T')  # Тип для идентификатора
E = TypeVar('E')  # Тип для сущности

logger = logging.getLogger(__name__)


class BaseRepository(RepositoryInterface[T, E]):
    """
    Базовый класс для всех репозиториев.
    
    Предоставляет общую функциональность для работы с базой данных SQLite,
    такую как управление соединениями и транзакциями.
    """
    
    def __init__(self, db_manager):
        """
        Инициализация репозитория.
        
        Args:
            db_manager: Менеджер базы данных
        """
        self._db_manager = db_manager
        
    @contextmanager
    def get_connection(self):
        """
        Контекстный менеджер для соединения с базой данных.
        
        Автоматически открывает и закрывает соединение с базой данных,
        а также управляет транзакциями (commit/rollback).
        
        Yields:
            Соединение с базой данных
        """
        return self._db_manager.get_connection()
            
    def execute_query(self, query: str, params: Tuple = (), fetchone: bool = False) -> Union[List[Dict[str, Any]], Dict[str, Any], None]:
        """
        Выполнение SQL-запроса.
        
        Args:
            query: SQL-запрос
            params: Параметры запроса
            fetchone: True, если нужно вернуть только одну запись
            
        Returns:
            Результат запроса в виде списка словарей, одного словаря или None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                
                if fetchone:
                    row = cursor.fetchone()
                    return dict(row) if row else None
                else:
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows] if rows else []
                    
        except Exception as e:
            logger.error(f"Ошибка выполнения запроса {query}: {str(e)}")
            raise
            
    def execute_update(self, query: str, params: Tuple = ()) -> int:
        """
        Выполнение запроса на изменение данных (INSERT, UPDATE, DELETE).
        
        Args:
            query: SQL-запрос
            params: Параметры запроса
            
        Returns:
            Количество измененных строк
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                return cursor.rowcount
                
        except Exception as e:
            logger.error(f"Ошибка выполнения запроса изменения {query}: {str(e)}")
            raise
            
    def to_entity(self, data: Dict[str, Any]) -> E:
        """
        Преобразование данных из базы данных в сущность.
        
        Args:
            data: Данные из базы данных
            
        Returns:
            Сущность
        """
        raise NotImplementedError("Метод to_entity должен быть переопределен в дочернем классе")
        
    def to_db_dict(self, entity: E) -> Dict[str, Any]:
        """
        Преобразование сущности в словарь для сохранения в базе данных.
        
        Args:
            entity: Сущность
            
        Returns:
            Словарь для сохранения в базе данных
        """
        raise NotImplementedError("Метод to_db_dict должен быть переопределен в дочернем классе")
        
    def get_by_id(self, id: T) -> Optional[E]:
        """
        Получение сущности по идентификатору.
        
        Args:
            id: Идентификатор сущности
            
        Returns:
            Сущность или None, если сущность не найдена
        """
        raise NotImplementedError("Метод get_by_id должен быть переопределен в дочернем классе")
    
    def get_all(self) -> List[E]:
        """
        Получение всех сущностей.
        
        Returns:
            Список всех сущностей
        """
        raise NotImplementedError("Метод get_all должен быть переопределен в дочернем классе")
    
    def create(self, entity: E) -> T:
        """
        Создание новой сущности.
        
        Args:
            entity: Сущность для создания
            
        Returns:
            Идентификатор созданной сущности
        """
        raise NotImplementedError("Метод create должен быть переопределен в дочернем классе")
    
    def update(self, id: T, entity: E) -> bool:
        """
        Обновление сущности.
        
        Args:
            id: Идентификатор сущности
            entity: Обновленная сущность
            
        Returns:
            True, если обновление прошло успешно, иначе False
        """
        raise NotImplementedError("Метод update должен быть переопределен в дочернем классе")
    
    def delete(self, id: T) -> bool:
        """
        Удаление сущности.
        
        Args:
            id: Идентификатор сущности
            
        Returns:
            True, если удаление прошло успешно, иначе False
        """
        raise NotImplementedError("Метод delete должен быть переопределен в дочернем классе") 