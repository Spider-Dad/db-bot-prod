import logging
import sys
import telebot
import os
import platform
from bot.repositories import (
    DatabaseManager,
    UserRepository,
    TemplateRepository,
    NotificationSettingRepository,
    NotificationLogRepository
)
from bot.services import (
    UserService,
    TemplateService,
    NotificationSettingService,
    NotificationLogService,
    BackupService,
    NotificationService
)
from bot.handlers import (
    UserHandler,
    TemplateHandler,
    NotificationSettingHandler,
    NotificationLogHandler,
    BackupHandler,
    GameHandler
)
from config import BOT_TOKEN, DATA_DIR

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

class SingleInstanceException(Exception):
    pass

def obtain_lock():
    """Получение блокировки для предотвращения запуска нескольких экземпляров"""
    lock_file = os.path.join(DATA_DIR, 'bot.lock')
    
    # Проверяем, запущен ли бот на Windows
    if platform.system() == 'Windows':
        logger.info("Запуск на Windows, блокировка файла пропущена")
        return None
    else:
        # Для Linux/Unix используем fcntl
        import fcntl
        try:
            # Создаем файл блокировки если его нет
            lock_fd = open(lock_file, 'w')
            # Пытаемся получить эксклюзивную блокировку
            fcntl.lockf(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Сохраняем дескриптор файла для поддержания блокировки
            return lock_fd
        except IOError:
            # Не удалось получить блокировку, значит экземпляр уже запущен
            logger.error("Не удалось получить блокировку. Возможно, бот уже запущен.")
            sys.exit(1)

def main():
    """Главная функция для запуска бота"""
    try:
        # Получаем блокировку для предотвращения запуска нескольких экземпляров
        lock_fd = obtain_lock()

        # Инициализация компонентов
        logger.info("Инициализация менеджера базы данных...")
        db_manager = DatabaseManager()
        
        # Инициализация репозиториев
        logger.info("Инициализация репозиториев...")
        user_repo = UserRepository(db_manager)
        template_repo = TemplateRepository(db_manager)
        setting_repo = NotificationSettingRepository(db_manager)
        log_repo = NotificationLogRepository(db_manager)
        
        # Инициализация сервисов
        logger.info("Инициализация сервисов...")
        user_service = UserService(user_repo)
        template_service = TemplateService(template_repo)
        setting_service = NotificationSettingService(setting_repo, template_repo)
        log_service = NotificationLogService(log_repo, user_repo, template_repo)
        backup_service = BackupService(db_manager)
        
        # Создание бота
        logger.info("Создание бота...")
        bot = telebot.TeleBot(BOT_TOKEN)
        
        # Создание и настройка обработчиков
        logger.info("Конфигурация обработчиков...")
        handlers = [
            UserHandler(bot, user_service),
            TemplateHandler(bot, template_service, user_service),
            NotificationSettingHandler(bot, setting_service, template_service),
            NotificationLogHandler(bot, log_service),
            BackupHandler(bot, backup_service),
            GameHandler(bot, user_service)
        ]
        
        # Регистрация обработчиков
        for handler in handlers:
            handler.register_handlers()
        
        # Настройка менеджера уведомлений
        logger.info("Настройка менеджера уведомлений...")
        notification_service = NotificationService(
            bot, 
            user_service, 
            template_service, 
            setting_service, 
            log_service
        )
        
        # Запуск менеджера уведомлений
        logger.info("Запуск менеджера уведомлений...")
        notification_service.start()
        
        # Запуск бота
        logger.info("Запуск бота...")
        logger.info("Бот успешно запущен!")
        bot.infinity_polling()

    except SingleInstanceException as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {str(e)}")
        raise
    finally:
        # Освобождаем блокировку при завершении
        if lock_fd is not None:
            lock_fd.close()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем")
    except Exception as e:
        logging.error(f"Бот остановлен из-за ошибки: {str(e)}")