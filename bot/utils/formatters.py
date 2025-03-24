"""
Модуль formatters содержит функции для форматирования данных.

Эти функции используются для форматирования текстовых сообщений,
дат, времени и других данных для отображения пользователям.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from bot.constants import MONTHS_RU, SAMPLE_TEMPLATE_DATA
from config import PHONE_PAY, NAME_PAY

logger = logging.getLogger(__name__)


def format_date(date_obj: datetime, format_type: str = 'full') -> str:
    """
    Форматирование даты.
    
    Args:
        date_obj: Объект datetime
        format_type: Тип формата ('full' - полный, 'short' - краткий, 'day_month' - день и месяц)
        
    Returns:
        Отформатированная дата
    """
    day = date_obj.day
    month = date_obj.month
    year = date_obj.year
    
    if format_type == 'full':
        return f"{day} {MONTHS_RU[month]['gen']} {year}"
    elif format_type == 'short':
        return f"{day:02d}.{month:02d}.{year}"
    elif format_type == 'day_month':
        return f"{day} {MONTHS_RU[month]['gen']}"
    else:
        return f"{day} {MONTHS_RU[month]['gen']} {year}"


def format_template(template: str, data: Dict[str, Any]) -> str:
    """
    Форматирование шаблона сообщения.
    
    Заменяет переменные в шаблоне на соответствующие значения из словаря данных.
    
    Args:
        template: Шаблон сообщения
        data: Словарь с данными для подстановки
        
    Returns:
        Отформатированное сообщение
    """
    # Используем регулярное выражение для поиска переменных в формате {variable}
    result = template
    
    # Находим все переменные в шаблоне
    variables = re.findall(r'{([^{}]+)}', template)
    
    # Заменяем каждую переменную на соответствующее значение
    for var in variables:
        placeholder = f"{{{var}}}"
        if var in data:
            result = result.replace(placeholder, str(data[var]))
    
    return result


def format_birthday_reminder(template: str, first_name: str, last_name: str, 
                          birth_date: str, days_before: int) -> str:
    """
    Форматирование напоминания о дне рождения.
    
    Args:
        template: Шаблон сообщения
        first_name: Имя именинника
        last_name: Фамилия именинника
        birth_date: Дата рождения в формате ДД.ММ.ГГГГ
        days_before: Количество дней до дня рождения
        
    Returns:
        Отформатированное сообщение
    """
    try:
        # Парсим дату рождения
        birth_date_obj = datetime.strptime(birth_date, "%d.%m.%Y")
        
        # Определяем дату дня рождения в текущем году
        now = datetime.now()
        birthday_this_year = datetime(now.year, birth_date_obj.month, birth_date_obj.day)
        
        # Если день рождения уже прошел в этом году, берем дату на следующий год
        if birthday_this_year < now:
            birthday_this_year = datetime(now.year + 1, birth_date_obj.month, birth_date_obj.day)
        
        # Определяем дату для напоминания (за days_before дней)
        reminder_date = birthday_this_year - timedelta(days=days_before)
        
        # Подготавливаем данные для форматирования
        data = {
            "name": f"{first_name} {last_name}",
            "first_name": first_name,
            "last_name": last_name,
            "date": format_date(birthday_this_year, 'day_month'),
            "date_before": format_date(reminder_date, 'day_month'),
            "days_until": str(days_before),
            "phone_pay": PHONE_PAY,
            "name_pay": NAME_PAY
        }
        
        # Форматируем шаблон
        return format_template(template, data)
        
    except Exception as e:
        logger.error(f"Ошибка форматирования напоминания о дне рождения: {str(e)}")
        return f"Ошибка форматирования сообщения. Обратитесь к администратору."


def preview_template(template: str) -> str:
    """
    Создание предварительного просмотра шаблона.
    
    Args:
        template: Шаблон сообщения
        
    Returns:
        Отформатированное сообщение с тестовыми данными
    """
    try:
        return format_template(template, SAMPLE_TEMPLATE_DATA)
    except Exception as e:
        logger.error(f"Ошибка создания предварительного просмотра шаблона: {str(e)}")
        return f"Ошибка форматирования шаблона. Проверьте синтаксис." 