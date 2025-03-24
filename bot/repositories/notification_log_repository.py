"""
Репозиторий журнала уведомлений.

Этот модуль содержит класс NotificationLogRepository, отвечающий за управление
записями в журнале уведомлений в базе данных.
"""

from typing import List, Dict, Optional, Any, Tuple
import logging
import sqlite3
from datetime import datetime, timedelta, date

from bot.core.models import NotificationLog
from bot.core.base_repository import BaseRepository
from bot.repositories.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class NotificationLogRepository(BaseRepository):
    """
    Репозиторий для работы с журналом уведомлений.
    
    Предоставляет методы для добавления, удаления и получения информации
    о записях журнала уведомлений из базы данных.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Инициализация репозитория журнала уведомлений.
        
        Args:
            db_manager: Менеджер базы данных
        """
        super().__init__(db_manager)
        
    def add_log(self, log: NotificationLog) -> Optional[int]:
        """
        Добавление новой записи в журнал уведомлений.
        
        Args:
            log: Объект записи журнала уведомлений для добавления
            
        Returns:
            Optional[int]: ID добавленной записи или None в случае ошибки
        """
        try:
            with self._db_manager.get_connection() as conn:
                # Проверяем, существует ли таблица
                conn.execute("""
                CREATE TABLE IF NOT EXISTS notification_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
                """)
                
                # Добавляем новую запись
                cursor = conn.execute("""
                INSERT INTO notification_logs (
                    user_id,
                    message,
                    status,
                    error_message,
                    created_at
                ) VALUES (?, ?, ?, ?, ?)
                """, (
                    log.user_id,
                    log.message,
                    log.status,
                    log.error_message,
                    log.created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
                
                logger.info(f"Новая запись журнала добавлена: user_id={log.user_id}, status={log.status}")
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"Ошибка добавления записи журнала: {str(e)}")
            return None
            
    def delete_log(self, log_id: int) -> bool:
        """
        Удаление записи из журнала уведомлений.
        
        Args:
            log_id: ID записи для удаления
            
        Returns:
            bool: True, если запись удалена успешно, иначе False
        """
        try:
            with self._db_manager.get_connection() as conn:
                # Проверяем, существует ли запись
                existing_log = conn.execute(
                    "SELECT id FROM notification_logs WHERE id = ?",
                    (log_id,)
                ).fetchone()
                
                if not existing_log:
                    logger.warning(f"Запись журнала с ID {log_id} не найдена для удаления")
                    return False
                    
                # Удаляем запись
                conn.execute("DELETE FROM notification_logs WHERE id = ?", (log_id,))
                logger.info(f"Запись журнала удалена: ID {log_id}")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка удаления записи журнала: {str(e)}")
            return False
            
    def get_log_by_id(self, log_id: int) -> Optional[NotificationLog]:
        """
        Получение записи журнала уведомлений по её ID.
        
        Args:
            log_id: ID записи
            
        Returns:
            Optional[NotificationLog]: Объект записи или None, если запись не найдена
        """
        try:
            with self._db_manager.get_connection() as conn:
                log_data = conn.execute("""
                SELECT 
                    id,
                    user_id,
                    message,
                    status,
                    error_message,
                    created_at
                FROM notification_logs
                WHERE id = ?
                """, (log_id,)).fetchone()
                
                if not log_data:
                    return None
                    
                return NotificationLog(
                    id=log_data['id'],
                    user_id=log_data['user_id'],
                    message=log_data['message'],
                    status=log_data['status'],
                    error_message=log_data['error_message'],
                    created_at=log_data['created_at']
                )
                
        except Exception as e:
            logger.error(f"Ошибка получения записи журнала: {str(e)}")
            return None
            
    def get_logs_by_user_id(self, user_id: int, limit: int = 100) -> List[NotificationLog]:
        """
        Получение записей журнала уведомлений по ID пользователя.
        
        Args:
            user_id: ID пользователя
            limit: Максимальное количество записей
            
        Returns:
            List[NotificationLog]: Список объектов записей
        """
        try:
            with self._db_manager.get_connection() as conn:
                logs_data = conn.execute("""
                SELECT 
                    id,
                    user_id,
                    message,
                    status,
                    error_message,
                    created_at
                FROM notification_logs
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """, (user_id, limit)).fetchall()
                
                logs = []
                for log_data in logs_data:
                    logs.append(NotificationLog(
                        id=log_data['id'],
                        user_id=log_data['user_id'],
                        message=log_data['message'],
                        status=log_data['status'],
                        error_message=log_data['error_message'],
                        created_at=log_data['created_at']
                    ))
                    
                return logs
                
        except Exception as e:
            logger.error(f"Ошибка получения записей журнала по ID пользователя: {str(e)}")
            return []
            
    def get_logs_by_status(self, status: str, limit: int = 100) -> List[NotificationLog]:
        """
        Получение записей журнала уведомлений по статусу.
        
        Args:
            status: Статус записи
            limit: Максимальное количество записей
            
        Returns:
            List[NotificationLog]: Список объектов записей
        """
        try:
            with self._db_manager.get_connection() as conn:
                logs_data = conn.execute("""
                SELECT 
                    id,
                    user_id,
                    message,
                    status,
                    error_message,
                    created_at
                FROM notification_logs
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ?
                """, (status, limit)).fetchall()
                
                logs = []
                for log_data in logs_data:
                    logs.append(NotificationLog(
                        id=log_data['id'],
                        user_id=log_data['user_id'],
                        message=log_data['message'],
                        status=log_data['status'],
                        error_message=log_data['error_message'],
                        created_at=log_data['created_at']
                    ))
                    
                return logs
                
        except Exception as e:
            logger.error(f"Ошибка получения записей журнала по статусу: {str(e)}")
            return []
            
    def get_logs_by_date_range(self, start_date: date, end_date: date, limit: int = 100) -> List[NotificationLog]:
        """
        Получение записей журнала уведомлений за указанный период времени.
        
        Args:
            start_date: Начальная дата периода
            end_date: Конечная дата периода
            limit: Максимальное количество записей
            
        Returns:
            List[NotificationLog]: Список объектов записей
        """
        try:
            with self._db_manager.get_connection() as conn:
                # Преобразуем даты в строки
                start_date_str = start_date.strftime("%Y-%m-%d 00:00:00")
                end_date_str = end_date.strftime("%Y-%m-%d 23:59:59")
                
                logs_data = conn.execute("""
                SELECT 
                    id,
                    user_id,
                    message,
                    status,
                    error_message,
                    created_at
                FROM notification_logs
                WHERE created_at BETWEEN ? AND ?
                ORDER BY created_at DESC
                LIMIT ?
                """, (start_date_str, end_date_str, limit)).fetchall()
                
                logs = []
                for log_data in logs_data:
                    logs.append(NotificationLog(
                        id=log_data['id'],
                        user_id=log_data['user_id'],
                        message=log_data['message'],
                        status=log_data['status'],
                        error_message=log_data['error_message'],
                        created_at=log_data['created_at']
                    ))
                    
                return logs
                
        except Exception as e:
            logger.error(f"Ошибка получения записей журнала по диапазону дат: {str(e)}")
            return []
            
    def get_all_logs(self, limit: int = 100) -> List[NotificationLog]:
        """
        Получение всех записей журнала уведомлений.
        
        Args:
            limit: Максимальное количество записей
            
        Returns:
            List[NotificationLog]: Список объектов записей
        """
        try:
            with self._db_manager.get_connection() as conn:
                logs_data = conn.execute("""
                SELECT 
                    id,
                    user_id,
                    message,
                    status,
                    error_message,
                    created_at
                FROM notification_logs
                ORDER BY created_at DESC
                LIMIT ?
                """, (limit,)).fetchall()
                
                logs = []
                for log_data in logs_data:
                    logs.append(NotificationLog(
                        id=log_data['id'],
                        user_id=log_data['user_id'],
                        message=log_data['message'],
                        status=log_data['status'],
                        error_message=log_data['error_message'],
                        created_at=log_data['created_at']
                    ))
                    
                return logs
                
        except Exception as e:
            logger.error(f"Ошибка получения всех записей журнала: {str(e)}")
            return []
            
    def delete_logs_older_than(self, days: int) -> int:
        """
        Удаление записей журнала уведомлений старше указанного количества дней.
        
        Args:
            days: Количество дней
            
        Returns:
            int: Количество удаленных записей
        """
        try:
            with self._db_manager.get_connection() as conn:
                # Рассчитываем дату отсечения
                cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
                
                # Подсчитываем количество записей для удаления
                count = conn.execute("""
                SELECT COUNT(*) as count
                FROM notification_logs
                WHERE created_at < ?
                """, (cutoff_date,)).fetchone()['count']
                
                # Удаляем записи
                conn.execute("""
                DELETE FROM notification_logs
                WHERE created_at < ?
                """, (cutoff_date,))
                
                logger.info(f"Удалены записи журнала старше {days} дней: {count} записей")
                return count
                
        except Exception as e:
            logger.error(f"Ошибка удаления старых записей журнала: {str(e)}")
            return 0
            
    def get_logs_with_errors(self, limit: int = 100) -> List[NotificationLog]:
        """
        Получение записей журнала уведомлений с ошибками.
        
        Args:
            limit: Максимальное количество записей
            
        Returns:
            List[NotificationLog]: Список объектов записей
        """
        try:
            with self._db_manager.get_connection() as conn:
                logs_data = conn.execute("""
                SELECT 
                    id,
                    user_id,
                    message,
                    status,
                    error_message,
                    created_at
                FROM notification_logs
                WHERE status = 'error' AND error_message IS NOT NULL
                ORDER BY created_at DESC
                LIMIT ?
                """, (limit,)).fetchall()
                
                logs = []
                for log_data in logs_data:
                    logs.append(NotificationLog(
                        id=log_data['id'],
                        user_id=log_data['user_id'],
                        message=log_data['message'],
                        status=log_data['status'],
                        error_message=log_data['error_message'],
                        created_at=log_data['created_at']
                    ))
                    
                return logs
                
        except Exception as e:
            logger.error(f"Ошибка получения записей журнала с ошибками: {str(e)}")
            return []
            
    def get_log_summary_by_date(self, date_value: date) -> Dict[str, int]:
        """
        Получение статистики по записям журнала за указанную дату.
        
        Args:
            date_value: Дата для анализа
            
        Returns:
            Dict[str, int]: Словарь с количеством записей по статусам
        """
        try:
            with self._db_manager.get_connection() as conn:
                # Преобразуем дату в строки
                start_date_str = date_value.strftime("%Y-%m-%d 00:00:00")
                end_date_str = date_value.strftime("%Y-%m-%d 23:59:59")
                
                status_counts = conn.execute("""
                SELECT 
                    status,
                    COUNT(*) as count
                FROM notification_logs
                WHERE created_at BETWEEN ? AND ?
                GROUP BY status
                """, (start_date_str, end_date_str)).fetchall()
                
                summary = {
                    'total': 0,
                    'success': 0,
                    'error': 0,
                    'warning': 0
                }
                
                for row in status_counts:
                    status = row['status']
                    count = row['count']
                    
                    if status in summary:
                        summary[status] = count
                    
                    summary['total'] += count
                    
                return summary
                
        except Exception as e:
            logger.error(f"Ошибка получения статистики журнала: {str(e)}")
            return {'total': 0, 'success': 0, 'error': 0, 'warning': 0} 