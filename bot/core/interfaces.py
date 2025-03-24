"""
Определение интерфейсов для компонентов приложения.

Этот модуль содержит интерфейсы (абстрактные базовые классы) для основных 
компонентов приложения, таких как репозитории и сервисы. Эти интерфейсы
определяют контракты, которым должны следовать конкретные реализации.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic, Union

T = TypeVar('T')  # Тип для идентификатора
E = TypeVar('E')  # Тип для сущности


class RepositoryInterface(Generic[T, E], ABC):
    """
    Базовый интерфейс для всех репозиториев.
    
    Определяет основные методы, которые должны реализовать все репозитории
    для работы с хранилищем данных.
    """
    
    @abstractmethod
    def get_by_id(self, id: T) -> Optional[E]:
        """
        Получение сущности по идентификатору.
        
        Args:
            id: Идентификатор сущности
            
        Returns:
            Сущность или None, если сущность не найдена
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[E]:
        """
        Получение всех сущностей.
        
        Returns:
            Список всех сущностей
        """
        pass
    
    @abstractmethod
    def create(self, entity: E) -> T:
        """
        Создание новой сущности.
        
        Args:
            entity: Сущность для создания
            
        Returns:
            Идентификатор созданной сущности
        """
        pass
    
    @abstractmethod
    def update(self, id: T, entity: E) -> bool:
        """
        Обновление сущности.
        
        Args:
            id: Идентификатор сущности
            entity: Обновленная сущность
            
        Returns:
            True, если обновление прошло успешно, иначе False
        """
        pass
    
    @abstractmethod
    def delete(self, id: T) -> bool:
        """
        Удаление сущности.
        
        Args:
            id: Идентификатор сущности
            
        Returns:
            True, если удаление прошло успешно, иначе False
        """
        pass


class ServiceInterface(ABC):
    """
    Базовый интерфейс для всех сервисов.
    
    Определяет базовую функциональность сервисов, которые представляют
    бизнес-логику приложения и работают с репозиториями.
    """
    
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


class NotificationStrategyInterface(ABC):
    """
    Интерфейс для стратегий уведомлений.
    
    Определяет методы, которые должны реализовать все стратегии
    отправки уведомлений.
    """
    
    @abstractmethod
    def should_notify(self, settings: Dict[str, Any], birthday_data: Dict[str, Any]) -> bool:
        """
        Проверка необходимости отправки уведомления.
        
        Args:
            settings: Настройки уведомления
            birthday_data: Данные о дне рождения
            
        Returns:
            True, если нужно отправить уведомление, иначе False
        """
        pass
    
    @abstractmethod
    def format_message(self, template: str, birthday_data: Dict[str, Any]) -> str:
        """
        Форматирование сообщения уведомления.
        
        Args:
            template: Шаблон сообщения
            birthday_data: Данные о дне рождения
            
        Returns:
            Отформатированное сообщение
        """
        pass 