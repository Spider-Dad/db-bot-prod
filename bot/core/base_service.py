"""
Базовый класс для сервисов.

Этот модуль содержит базовый класс для всех сервисов, которые реализуют
бизнес-логику приложения и используют репозитории для доступа к данным.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, TypeVar, Optional

from .interfaces import ServiceInterface, RepositoryInterface

T = TypeVar('T')  # Тип для идентификатора
E = TypeVar('E')  # Тип для сущности

logger = logging.getLogger(__name__)


class BaseService(ServiceInterface, ABC):
    """
    Базовый класс для всех сервисов.
    
    Сервисы инкапсулируют бизнес-логику приложения и используют репозитории
    для доступа к данным. Этот базовый класс предоставляет общие методы для
    работы с репозиториями и обработки ошибок.
    """
    
    def __init__(self, *args, **kwargs):
        """
        Инициализация сервиса.
        
        Args:
            *args: Позиционные аргументы
            **kwargs: Именованные аргументы, которые могут включать репозитории и другие зависимости
        """
        pass
    
    def log_error(self, message: str, exception: Optional[Exception] = None) -> None:
        """
        Логирование ошибки.
        
        Args:
            message: Сообщение об ошибке
            exception: Исключение (если есть)
        """
        if exception:
            logger.error(f"{message}: {str(exception)}")
        else:
            logger.error(message)
    
    def log_info(self, message: str) -> None:
        """
        Логирование информационного сообщения.
        
        Args:
            message: Информационное сообщение
        """
        logger.info(message)
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """
        Валидация входных данных.
        
        Args:
            data: Данные для валидации
            
        Returns:
            True, если данные валидны, иначе False
        """
        # Базовая реализация - всегда возвращает True
        # Переопределяется в дочерних классах
        return True
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """
        Выполнение основной бизнес-логики сервиса.
        
        Args:
            *args: Позиционные аргументы
            **kwargs: Именованные аргументы
            
        Returns:
            Результат выполнения бизнес-логики
        """
        pass 