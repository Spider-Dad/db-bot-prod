"""
Модуль validators содержит функции для валидации данных.

Эти функции используются для проверки корректности данных, введенных
пользователями или получаемых из базы данных.
"""

import re
import logging
from typing import List, Set, Dict, Any, Optional, Tuple
from datetime import datetime

from bot.constants import ALLOWED_HTML_TAGS, TEMPLATE_VARIABLES

logger = logging.getLogger(__name__)


def validate_html(text: str) -> Tuple[bool, Optional[List[str]]]:
    """
    Проверка HTML-тегов в тексте.
    
    Проверяет, что в тексте используются только разрешенные HTML-теги.
    
    Args:
        text: Текст для проверки
        
    Returns:
        Кортеж (is_valid, invalid_tags), где:
        - is_valid: True, если все HTML-теги допустимы
        - invalid_tags: список недопустимых тегов или None, если is_valid = True
    """
    # Находим все HTML-теги в тексте
    tags = re.findall(r'<([a-zA-Z0-9_-]+)[^>]*>', text)
    closing_tags = re.findall(r'</([a-zA-Z0-9_-]+)>', text)
    
    # Объединяем найденные теги
    all_tags = set(tags + closing_tags)
    
    # Проверяем, есть ли недопустимые теги
    invalid_tags = [tag for tag in all_tags if tag not in ALLOWED_HTML_TAGS]
    
    return len(invalid_tags) == 0, invalid_tags if invalid_tags else None


def validate_template_variables(text: str) -> Tuple[bool, Optional[List[str]]]:
    """
    Проверка переменных шаблона в тексте.
    
    Проверяет, что в тексте используются только допустимые переменные шаблона.
    
    Args:
        text: Текст для проверки
        
    Returns:
        Кортеж (is_valid, invalid_vars), где:
        - is_valid: True, если все переменные допустимы
        - invalid_vars: список недопустимых переменных или None, если is_valid = True
    """
    # Находим все переменные в фигурных скобках
    variables = re.findall(r'{([^{}]+)}', text)
    
    # Получаем чистые имена переменных из списка TEMPLATE_VARIABLES
    allowed_vars = [var.strip('{}') for var in TEMPLATE_VARIABLES]
    
    # Проверяем, есть ли недопустимые переменные
    invalid_vars = [var for var in variables if var not in allowed_vars]
    
    return len(invalid_vars) == 0, invalid_vars if invalid_vars else None


def validate_date_format(date_str: str) -> bool:
    """
    Проверка формата даты.
    
    Проверяет, что строка соответствует формату ДД.ММ.ГГГГ.
    
    Args:
        date_str: Строка с датой
        
    Returns:
        True, если формат даты корректен, иначе False
    """
    try:
        datetime.strptime(date_str, "%d.%m.%Y")
        return True
    except ValueError:
        return False


def validate_time_format(time_str: str) -> bool:
    """
    Проверка формата времени.
    
    Проверяет, что строка соответствует формату ЧЧ:ММ.
    
    Args:
        time_str: Строка с временем
        
    Returns:
        True, если формат времени корректен, иначе False
    """
    try:
        datetime.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False


def validate_birth_date(date_str: str) -> Tuple[bool, Optional[str]]:
    """
    Проверка даты рождения.
    
    Проверяет, что строка содержит валидную дату рождения в формате ДД.ММ.ГГГГ,
    и что эта дата не находится в будущем.
    
    Args:
        date_str: Строка с датой рождения
        
    Returns:
        Кортеж (is_valid, error_message), где:
        - is_valid: True, если дата корректна
        - error_message: сообщение об ошибке или None, если is_valid = True
    """
    # Проверяем формат даты
    if not validate_date_format(date_str):
        return False, "Неверный формат даты. Используйте формат ДД.ММ.ГГГГ."
    
    try:
        # Парсим дату
        birth_date = datetime.strptime(date_str, "%d.%m.%Y").date()
        
        # Проверяем, что дата не в будущем
        current_date = datetime.now().date()
        if birth_date > current_date:
            return False, "Дата рождения не может быть в будущем."
        
        # Проверяем, что дата не слишком далеко в прошлом (например, больше 150 лет назад)
        years_diff = (current_date.year - birth_date.year)
        if years_diff > 150:
            return False, "Указанная дата рождения слишком давняя."
        
        return True, None
    except ValueError:
        return False, "Неверный формат даты. Используйте формат ДД.ММ.ГГГГ." 