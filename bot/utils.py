from datetime import datetime
from typing import Optional

def validate_date(date_str: str) -> Optional[datetime]:
    """Проверка формата строки даты"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None

def format_date(date: datetime) -> str:
    """Форматирование даты в строку"""
    return date.strftime("%Y-%m-%d")

def is_valid_username(username: str) -> bool:
    """Проверка корректности имени пользователя Telegram"""
    return bool(username and username.strip() and len(username) >= 5)