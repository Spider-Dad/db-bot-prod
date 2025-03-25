import os
import logging
from typing import List
from dotenv import load_dotenv
from bot.constants import DEFAULT_NOTIFICATION_TEMPLATES, DEFAULT_NOTIFICATION_SETTINGS

"""
Конфигурация приложения.

Для локальной разработки данные будут храниться в директории data/ в корне проекта.
На сервере данные хранятся в абсолютном пути /data/.

Для запуска на сервере установите переменную окружения SERVER_ENV=production.
"""

# Загрузка переменных из файла .env
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация бота
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Не установлена переменная окружения BOT_TOKEN")

# Преобразование списка ADMIN_IDS из строки с разделителями-запятыми в список целых чисел
ADMIN_IDS: List[int] = [
    int(id_str.strip()) 
    for id_str in os.environ.get("ADMIN_IDS", "").split(",") 
    if id_str.strip().isdigit()
] or [100116667, 908546990]  # Актуальные admin IDs

# Настройки для шаблонов сообщений
PHONE_PAY = os.environ.get("PHONE_PAY", "7 920 132 2534")
NAME_PAY = os.environ.get("NAME_PAY", "Диана Ибрагимовна Рыжова")

# Логируем значения переменных
logger.info(f"PHONE_PAY: {PHONE_PAY}")
logger.info(f"NAME_PAY: {NAME_PAY}")

# Конфигурация базы данных
# Определяем, где запущен код - локально или на сервере
is_server = os.environ.get("SERVER_ENV") == "production"

# Выбираем путь в зависимости от окружения
if is_server:
    DATA_DIR = "/data"  # Абсолютный путь на сервере
else:
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")  # Локальный путь для тестирования

logger.info(f"Используется DATA_DIR: {DATA_DIR} ({'сервер' if is_server else 'локальная разработка'})")

# Проверяем существование директории data и создаем её при необходимости
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

DB_PATH = os.path.join(DATA_DIR, "birthday_bot.db")
SCHEMA_PATH = os.path.join(DATA_DIR, "db_schema.sql")

# Логируем пути
logger.info(f"DB_PATH: {DB_PATH}")
logger.info(f"SCHEMA_PATH: {SCHEMA_PATH}")

# Настройки и шаблоны уведомлений по умолчанию импортируются из constants.py