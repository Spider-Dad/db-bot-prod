import logging
import sys
import telebot
import os
import fcntl
from bot import Database, NotificationManager, BotHandlers
from config import BOT_TOKEN, DATA_DIR

# Configure logging
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
    try:
        # Создаем файл блокировки если его нет
        lock_fd = open(lock_file, 'w')
        # Пытаемся получить эксклюзивную блокировку
        fcntl.lockf(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Сохраняем дескриптор файла для поддержания блокировки
        return lock_fd
    except IOError:
        logger.error("Бот уже запущен! Останавливаем этот экземпляр.")
        raise SingleInstanceException("Бот уже запущен в другом процессе")

def main():
    """Main function to start the bot"""
    try:
        # Проверяем, не запущен ли уже бот
        lock_fd = obtain_lock()

        # Initialize components
        logger.info("Инициализация базы данных...")
        db = Database()

        logger.info("Создание бота...")
        bot = telebot.TeleBot(BOT_TOKEN)

        logger.info("Настройка менеджера уведомлений...")
        notification_manager = NotificationManager(bot, db)

        logger.info("Конфигурация обработчиков...")
        handlers = BotHandlers(bot, db, notification_manager)
        handlers.register_handlers()

        # Start notification manager
        logger.info("Запуск менеджера уведомлений...")
        notification_manager.start()

        # Start bot and setup command menu
        logger.info("Запуск бота...")
        logger.info("Настройка меню команд...")
        handlers.setup_command_menu()  # Setup command menu after bot is initialized
        bot.infinity_polling()

    except SingleInstanceException as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {str(e)}")
        raise
    finally:
        # Освобождаем блокировку при завершении
        if 'lock_fd' in locals():
            lock_fd.close()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем")
    except Exception as e:
        logging.error(f"Бот остановлен из-за ошибки: {str(e)}")