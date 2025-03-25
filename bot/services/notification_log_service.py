"""
Сервис для работы с журналом уведомлений.

Этот модуль содержит сервис, предоставляющий бизнес-логику для операций
с записями журнала уведомлений.
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import date, datetime, timedelta

from bot.core.base_service import BaseService
from bot.core.models import NotificationLog, User
from bot.repositories.notification_log_repository import NotificationLogRepository
from bot.repositories.user_repository import UserRepository
from bot.repositories.template_repository import TemplateRepository

logger = logging.getLogger(__name__)


class NotificationLogService(BaseService):
    """
    Сервис для работы с журналом уведомлений.
    
    Предоставляет бизнес-логику для операций с журналом уведомлений,
    используя NotificationLogRepository для доступа к данным.
    """
    
    def __init__(self, log_repository: NotificationLogRepository, user_repository: UserRepository = None, template_repository: TemplateRepository = None):
        """
        Инициализация сервиса журнала уведомлений.
        
        Args:
            log_repository: Репозиторий журнала уведомлений
            user_repository: Репозиторий пользователей (опционально)
            template_repository: Репозиторий шаблонов (опционально)
        """
        super().__init__()
        self.log_repository = log_repository
        self.user_repository = user_repository
        self.template_repository = template_repository
    
    def add_log(self, log: NotificationLog) -> Optional[int]:
        """
        Добавление новой записи в журнал.
        
        Args:
            log: Запись для добавления
            
        Returns:
            ID добавленной записи или None в случае ошибки
        """
        return self.log_repository.add_log(log)
    
    def log_notification(self, user_id: int, message: str, status: str = "success", error_message: str = None) -> Optional[int]:
        """
        Логирование уведомления.
        
        Args:
            user_id: ID пользователя
            message: Текст сообщения
            status: Статус уведомления (success, error, warning)
            error_message: Текст ошибки (если есть)
            
        Returns:
            ID добавленной записи или None в случае ошибки
        """
        log = NotificationLog(
            user_id=user_id,
            message=message,
            status=status,
            error_message=error_message,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        return self.add_log(log)
    
    def get_log_by_id(self, log_id: int) -> Optional[NotificationLog]:
        """
        Получение записи журнала по ID.
        
        Args:
            log_id: ID записи
            
        Returns:
            Запись или None, если запись не найдена
        """
        return self.log_repository.get_log_by_id(log_id)
    
    def get_logs_by_user_id(self, user_id: int, limit: int = 100) -> List[NotificationLog]:
        """
        Получение записей журнала по ID пользователя.
        
        Args:
            user_id: ID пользователя
            limit: Максимальное количество записей
            
        Returns:
            Список записей
        """
        return self.log_repository.get_logs_by_user_id(user_id, limit)
    
    def get_logs_by_status(self, status: str, limit: int = 100) -> List[NotificationLog]:
        """
        Получение записей журнала по статусу.
        
        Args:
            status: Статус записи
            limit: Максимальное количество записей
            
        Returns:
            Список записей
        """
        return self.log_repository.get_logs_by_status(status, limit)
    
    def get_logs_by_date_range(self, start_date: date, end_date: date, limit: int = 100) -> List[NotificationLog]:
        """
        Получение записей журнала за указанный период.
        
        Args:
            start_date: Начальная дата периода
            end_date: Конечная дата периода
            limit: Максимальное количество записей
            
        Returns:
            Список записей
        """
        return self.log_repository.get_logs_by_date_range(start_date, end_date, limit)
    
    def get_today_logs(self, limit: int = 100) -> List[NotificationLog]:
        """
        Получение записей журнала за сегодня.
        
        Args:
            limit: Максимальное количество записей
            
        Returns:
            Список записей
        """
        today = datetime.now().date()
        return self.get_logs_by_date_range(today, today, limit)
    
    def get_week_logs(self, limit: int = 500) -> List[NotificationLog]:
        """
        Получение записей журнала за последнюю неделю.
        
        Args:
            limit: Максимальное количество записей
            
        Returns:
            Список записей
        """
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        return self.get_logs_by_date_range(week_ago, today, limit)
    
    def get_all_logs(self, limit: int = 100) -> List[NotificationLog]:
        """
        Получение всех записей журнала.
        
        Args:
            limit: Максимальное количество записей
            
        Returns:
            Список записей
        """
        return self.log_repository.get_all_logs(limit)
    
    def get_logs_with_errors(self, limit: int = 100) -> List[NotificationLog]:
        """
        Получение записей журнала с ошибками.
        
        Args:
            limit: Максимальное количество записей
            
        Returns:
            Список записей
        """
        return self.log_repository.get_logs_with_errors(limit)
    
    def delete_log(self, log_id: int) -> bool:
        """
        Удаление записи из журнала.
        
        Args:
            log_id: ID записи
            
        Returns:
            True, если удаление прошло успешно, иначе False
        """
        return self.log_repository.delete_log(log_id)
    
    def delete_logs_older_than(self, days: int) -> int:
        """
        Удаление записей журнала старше указанного количества дней.
        
        Args:
            days: Количество дней
            
        Returns:
            Количество удаленных записей
        """
        return self.log_repository.delete_logs_older_than(days)
    
    def clean_old_logs(self, retention_days: int = 30) -> int:
        """
        Очистка старых записей журнала.
        
        Args:
            retention_days: Количество дней для хранения записей
            
        Returns:
            Количество удаленных записей
        """
        return self.delete_logs_older_than(retention_days)
    
    def get_log_summary_by_date(self, date_value: date) -> Dict[str, int]:
        """
        Получение статистики по записям журнала за указанную дату.
        
        Args:
            date_value: Дата для анализа
            
        Returns:
            Словарь с количеством записей по статусам
        """
        return self.log_repository.get_log_summary_by_date(date_value)
    
    def get_today_summary(self) -> Dict[str, int]:
        """
        Получение статистики по записям журнала за сегодня.
        
        Returns:
            Словарь с количеством записей по статусам
        """
        today = datetime.now().date()
        return self.get_log_summary_by_date(today)
    
    def get_week_summary(self) -> Dict[str, int]:
        """
        Получение статистики по записям журнала за последнюю неделю.
        
        Returns:
            Словарь с количеством записей по статусам
        """
        week_summary = {
            'total': 0,
            'success': 0,
            'error': 0,
            'warning': 0
        }
        
        today = datetime.now().date()
        for i in range(7):
            date_value = today - timedelta(days=i)
            day_summary = self.get_log_summary_by_date(date_value)
            
            for key in week_summary:
                week_summary[key] += day_summary.get(key, 0)
                
        return week_summary
    
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