import logging
from config import PHONE_PAY, NAME_PAY
import re
from typing import List, Dict, Tuple
from bot.constants import (
    MONTHS_RU, ALLOWED_HTML_TAGS, TEMPLATE_VARIABLES, 
    SAMPLE_TEMPLATE_DATA, TEMPLATE_HELP_TEXT, EMOJI
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.ERROR) # Настройка логирования для вывода ошибок

from datetime import datetime, timedelta
import re
from typing import List, Dict

def format_birthday_reminder(template: str, first_name: str, last_name: str, 
                           birth_date: str, days_before: int) -> str:
    """Форматирование сообщений с напоминанием о дне рождения с поддержкой HTML"""
    try:
        name = f"{first_name} {last_name}".strip()
        birth_date_obj = datetime.strptime(birth_date, "%Y-%m-%d")

        # Получаем дату дня рождения в этом году
        current_year = datetime.now().year
        birthday_this_year = birth_date_obj.replace(year=current_year)

        # Форматируем даты с русскими названиями месяцев
        date = f"{birthday_this_year.day:02d} {MONTHS_RU[birthday_this_year.month]['gen']}"
        date_before = f"{(birthday_this_year - timedelta(days=1)).day:02d} {MONTHS_RU[(birthday_this_year - timedelta(days=1)).month]['gen']}"

        # Создаем словарь всех доступных переменных
        template_vars = {
            "name": name,
            "first_name": first_name,
            "last_name": last_name,
            "date": date,
            "date_before": date_before,
            "days_until": str(days_before),
            "phone_pay": PHONE_PAY,  # Добавляем переменную phone_pay
            "name_pay": NAME_PAY     # Добавляем переменную name_pay
        }

        # Логируем значения для отладки
        logger.info(f"Template variables: {template_vars}")

        # Заменяем переменные, которые есть в шаблоне
        result = template
        for var_name, var_value in template_vars.items():
            var_placeholder = "{" + var_name + "}"
            if var_placeholder in template:
                result = result.replace(var_placeholder, var_value)

        return result
    except Exception as e:
        logger.error(f"Ошибка форматирования напоминания о дне события: {str(e)}")
        return template  # Возвращаем исходный шаблон в случае ошибки

def get_welcome_message(is_admin: bool = False, is_authorized: bool = False) -> str:
    """Получение приветственного сообщения для разных типов пользователей"""

    # Для неавторизованного пользователя
    if not is_authorized:
        return f"""Уже добавляем тебя в систему уведомлений о событиях нашей службы. Подожди немного...🕒
        
        Пожалуйста, установи @username, если у тебя его нет. Это нужно, чтобы все работало исправно🤖"""

    # Базовое приветствие для всех авторизованных пользователей
    base_message = """<b>Привет!</b> 👋
Я бот для уведомлений о событиях нашей службы"""

    # Для администратора
    if is_admin:
        return f"""{base_message}

🦸‍♂️✨ Ты являешься <b>администратором</b>.
Для тебя доступен <b>полный функционал</b> бота."""

    # Для обычного пользователя
    return f"""{base_message}
🦸‍♂️ Ты являешься <b>пользователем бота</b>.

Доступные команды:
• /start - Начать работу с ботом
• /birthdays - Список дней рождений"""

def get_birthday_list_message(birthdays: list) -> str:
    """Форматирование сообщения со списком дней рождения"""
    if not birthdays:
        return "В базе данных нет дней рождения."

    message = "📅 Список дней рождения на текущий год:\n\n"
    current_month = None

    for birthday in birthdays:
        birth_date = datetime.strptime(birthday['birth_date'], "%Y-%m-%d")
        month_num = birth_date.month

        # Форматируем дату с русским названием месяца в родительном падеже
        date = f"{birth_date.day:02d} {MONTHS_RU[month_num]['gen']}"

        if month_num != current_month:
            if current_month is not None:  # Добавляем дополнительный перенос строки между месяцами
                message += "\n"
            current_month = month_num
            message += f"🗓 {MONTHS_RU[month_num]['nom']}:\n"

        name = f"{birthday['first_name']}"
        if birthday['last_name']:
            name += f" {birthday['last_name']}"
        message += f"   🎂 {name} - {date}\n"

    return message

def get_new_user_notification(first_name: str) -> str:
    """Получение уведомления для новых пользователей"""
    return f"""✨ <b>Добро пожаловать, {first_name}!</b>

    Ты успешно добавлен в систему напоминаний о событиях нашей службы.

    Доступные команды:
    • /start - Информация о боте
    • /birthdays - Список дней рождений коллег

    Приятного использования! 🎉"""

def get_new_user_request_notification(user_info: dict) -> str:
        """Формирование уведомления для администраторов о новом пользователе"""
        username = f"@{user_info.get('username', '❗️username отсутствует')}"
        name = f"{user_info['first_name']}"
        if user_info.get('last_name', ''):
            name += f" {user_info.get('last_name', '')}"
        return f"""🆕 <b>Новый запрос на доступ!</b>

    👤 <b>Пользователь:</b> {name}
    🔍 <b>Username:</b> {username}
    🆔 <b>Telegram ID:</b> {user_info['telegram_id']}

    Для добавления пользователя используй команду:
    <code>/add_user {username} {user_info['first_name']} {user_info['last_name']} YYYY-MM-DD</code>
    Замени YYYY-MM-DD на дату рождения пользователя в формате год-месяц-день."""

def validate_template_html(template: str) -> bool:
    """Проверка HTML-тегов шаблона"""
    tag_pattern = re.compile(r'</?([a-z-]+)(?:\s+[^>]*)?>')

    # Находим все HTML-теги в шаблоне
    tags = tag_pattern.findall(template)

    # Проверяем, что все теги разрешены
    return all(tag.lower() in ALLOWED_HTML_TAGS for tag in tags)

def validate_template_variables(template: str) -> Tuple[bool, List[str]]:
    """
    Проверка переменных в шаблоне.
    Возвращает кортеж (is_valid, invalid_vars).
    """
    # Находим все переменные в шаблоне {variable}
    var_pattern = re.compile(r'\{([^}]+)\}')
    found_vars = var_pattern.findall(template)

    # Проверяем каждую найденную переменную
    invalid_vars = []
    for var in found_vars:
        var_with_braces = "{" + var + "}"
        if var_with_braces not in TEMPLATE_VARIABLES:
            invalid_vars.append(var)

    return (len(invalid_vars) == 0, invalid_vars)


def get_template_help() -> str:
    """Получение справки по форматированию шаблонов"""
    return TEMPLATE_HELP_TEXT

def preview_template_message(template: str, previews: List[tuple]) -> str:
    """Форматирование сообщения предварительного просмотра с индикаторами emoji"""
    response = "📝 <b>Предварительный просмотр шаблона</b>\n\n"
    response += "📋 <i>Исходный шаблон:</i>\n"
    response += f"<code>{template}</code>\n\n"
    response += "🔍 <b>Примеры сообщений:</b>\n\n"
    
    # Используем эмодзи из констант
    for i, (preview_type, message) in enumerate(previews):
        emoji = EMOJI.get(preview_type, EMOJI["general"])
        response += f"{emoji} <b>{preview_type.capitalize()}:</b>\n"
        response += f"{message}\n\n"

    return response