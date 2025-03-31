"""
Сервис для работы с резервными копиями базы данных.

Этот модуль содержит сервис, предоставляющий бизнес-логику для операций
с резервными копиями базы данных.
"""

import logging
import os
from typing import List, Optional, Any
from datetime import datetime

from bot.core.base_service import BaseService
from bot.repositories.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class BackupService(BaseService):
    """
    Сервис для работы с резервными копиями базы данных.
    
    Предоставляет бизнес-логику для операций с резервными копиями,
    используя DatabaseManager для доступа к функциям резервного копирования.
    """
    
    def __init__(self, database_manager: DatabaseManager):
        """
        Инициализация сервиса резервного копирования.
        
        Args:
            database_manager: Менеджер базы данных
        """
        super().__init__()
        self.database_manager = database_manager
    
    def create_backup(self, comment: str = None) -> Optional[str]:
        """
        Создание резервной копии базы данных.
        
        Args:
            comment: Комментарий к резервной копии
            
        Returns:
            Имя файла резервной копии или None в случае ошибки
        """
        try:
            backup_name = self.database_manager.backup_database(comment)
            logger.info(f"Создана резервная копия базы данных: {backup_name}")
            return backup_name
        except Exception as e:
            logger.error(f"Ошибка при создании резервной копии: {e}")
            return None
    
    def get_backup_list(self) -> List[dict]:
        """
        Получение списка резервных копий.
        
        Returns:
            Список резервных копий в формате словарей с информацией о копии
        """
        try:
            return self.database_manager.get_backup_list()
        except Exception as e:
            logger.error(f"Ошибка при получении списка резервных копий: {e}")
            return []
    
    def restore_from_backup(self, backup_name: str) -> bool:
        """
        Восстановление базы данных из резервной копии.
        
        Args:
            backup_name: Имя файла резервной копии
            
        Returns:
            True, если восстановление прошло успешно, иначе False
        """
        try:
            # Получаем полный путь к файлу резервной копии
            backup_path = self.get_backup_path(backup_name)
            
            if not backup_path:
                logger.warning(f"Не удалось найти резервную копию: {backup_name}")
                return False
                
            # Восстанавливаем из резервной копии
            result = self.database_manager.restore_from_backup(backup_path)
            if result:
                logger.info(f"База данных успешно восстановлена из копии: {backup_name}")
            else:
                logger.warning(f"Не удалось восстановить базу данных из копии: {backup_name}")
            return result
        except Exception as e:
            logger.error(f"Ошибка при восстановлении из резервной копии {backup_name}: {e}")
            return False
    
    def delete_backup(self, backup_name: str) -> bool:
        """
        Удаление резервной копии.
        
        Args:
            backup_name: Имя файла резервной копии
            
        Returns:
            True, если удаление прошло успешно, иначе False
        """
        try:
            # Проверяем, существует ли резервная копия
            backup_path = self.get_backup_path(backup_name)
            
            if not backup_path:
                logger.warning(f"Не удалось найти резервную копию: {backup_name}")
                return False
                
            # Удаляем резервную копию
            result = self.database_manager.delete_backup(backup_name)
            if result:
                logger.info(f"Резервная копия успешно удалена: {backup_name}")
            else:
                logger.warning(f"Не удалось удалить резервную копию: {backup_name}")
            return result
        except Exception as e:
            logger.error(f"Ошибка при удалении резервной копии {backup_name}: {e}")
            return False
    
    def create_scheduled_backup(self) -> Optional[str]:
        """
        Создание плановой резервной копии с автоматически генерируемым комментарием.
        
        Returns:
            Имя файла резервной копии или None в случае ошибки
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        comment = f"Плановая резервная копия от {timestamp}"
        return self.create_backup(comment)
    
    def clean_old_backups(self, keep_count: int = 10) -> int:
        """
        Удаление старых резервных копий, оставляя указанное количество последних.
        
        Args:
            keep_count: Количество копий, которые нужно сохранить
            
        Returns:
            Количество удаленных копий
        """
        try:
            # Получаем список резервных копий
            backups = self.get_backup_list()
            
            # Сортируем по дате создания (от новых к старым)
            backups.sort(key=lambda x: x.get('date', ''), reverse=True)
            
            # Определяем, какие копии нужно удалить
            backups_to_delete = backups[keep_count:] if keep_count < len(backups) else []
            
            # Удаляем старые копии
            deleted_count = 0
            for backup in backups_to_delete:
                backup_name = backup.get('filename')
                if backup_name and self.delete_backup(backup_name):
                    deleted_count += 1
            
            logger.info(f"Удалено {deleted_count} старых резервных копий")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Ошибка при очистке старых резервных копий: {e}")
            return 0
    
    def backup_exists(self, backup_name: str) -> bool:
        """
        Проверка существования резервной копии.
        
        Args:
            backup_name: Имя файла резервной копии
            
        Returns:
            True, если копия существует, иначе False
        """
        return self.database_manager.backup_exists(backup_name)
    
    def get_backup_path(self, backup_name: str) -> Optional[str]:
        """
        Получение полного пути к файлу резервной копии.
        
        Args:
            backup_name: Имя файла резервной копии
            
        Returns:
            Полный путь к файлу резервной копии или None, если файл не найден
        """
        try:
            return self.database_manager.get_backup_path(backup_name)
        except Exception as e:
            logger.error(f"Ошибка при получении пути к резервной копии {backup_name}: {e}")
            return None
    
    def get_backup_info(self, backup_name: str) -> Optional[dict]:
        """
        Получение информации о резервной копии.
        
        Args:
            backup_name: Имя файла резервной копии
            
        Returns:
            Словарь с информацией о копии или None, если копия не найдена
        """
        try:
            # Получаем список всех резервных копий
            backups = self.get_backup_list()
            
            # Ищем нужную копию
            for backup in backups:
                if backup.get('filename') == backup_name:
                    return backup
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении информации о резервной копии {backup_name}: {e}")
            return None
    
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