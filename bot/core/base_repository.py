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


class BaseRepository(RepositoryInterface[T, E], ABC):
    """
    Базовый класс для всех репозиториев.
    
    Предоставляет общую функциональность для работы с базой данных SQLite,
    такую как управление соединениями и транзакциями.
    """
    
    def __init__(self, db_path: str):
        """
        Инициализация репозитория.
        
        Args:
            db_path: Путь к файлу базы данных SQLite
        """
        self.db_path = db_path
        
    @contextmanager
    def get_connection(self):
        """
        Контекстный менеджер для соединения с базой данных.
        
        Автоматически открывает и закрывает соединение с базой данных,
        а также управляет транзакциями (commit/rollback).
        
        Yields:
            Соединение с базой данных
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка базы данных: {str(e)}")
            raise
        finally:
            conn.close()
            
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
            
    @abstractmethod
    def to_entity(self, data: Dict[str, Any]) -> E:
        """
        Преобразование данных из базы данных в сущность.
        
        Args:
            data: Данные из базы данных
            
        Returns:
            Сущность
        """
        pass
        
    @abstractmethod
    def to_db_dict(self, entity: E) -> Dict[str, Any]:
        """
        Преобразование сущности в словарь для сохранения в базе данных.
        
        Args:
            entity: Сущность
            
        Returns:
            Словарь для сохранения в базе данных
        """
        pass 