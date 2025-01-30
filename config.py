import os
import logging
from typing import List

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
# Получаем абсолютный путь к папке data
DATA_DIR = "/data" # Используем абсолютный путь

# Проверяем существование директории data и создаем её при необходимости
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

DB_PATH = os.path.join(DATA_DIR, "birthday_bot.db")
SCHEMA_PATH = os.path.join(DATA_DIR, "db_schema.sql")

# Логируем пути
logger.info(f"DB_PATH: {DB_PATH}")
logger.info(f"SCHEMA_PATH: {SCHEMA_PATH}")

# Настройки уведомлений по умолчанию
DEFAULT_NOTIFICATION_SETTINGS = [
    {
        "days_before": 3,
        "time": "10:00",
        "template": """<b>Привет!</b> 👋

<i>{date}</i> день рождения у <b>{name}</b>. Если хочешь принять участие в поздравительном конверте, прошу перевести взнос по номеру телефона <code>{phone_pay}</code> на Альфу или Тинькофф до <i>{date_before}</i>.

<b>Получатель:</b> {name_pay}.

⚠️ Пожалуйста, не переводи деньги в другие банки, даже если приложение будет предлагать варианты.
В комментарии укажи «<code>ДР {name}</code>»."""
    },
    {
        "days_before": 1,
        "time": "09:00",
        "template": """<b>Напоминание! ⏰</b>

<i>Завтра, {date}</i>, день рождения у <b>{name}</b>. 

Если ты еще не перевел(а) деньги на подарок, самое время это сделать!
• Номер: <code>{phone_pay}</code>
• Банки: Альфа или Тинькофф
• Получатель: <i>{name_pay}</i>
• Комментарий: <code>ДР {name}</code>"""
    },
    {
        "days_before": 0,
        "time": "09:00",
        "template": """<b>🎂 С днем рождения!</b>

Сегодня день рождения у <b>{name}</b>.
Не забудь поздравить!"""
    }
]