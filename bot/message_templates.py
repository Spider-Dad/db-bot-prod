import logging
from config import PHONE_PAY, NAME_PAY
import re
from typing import List, Dict, Tuple

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

        # Русские названия месяцев в родительном падеже
        MONTHS_RU = {
            1: "января", 2: "февраля", 3: "марта", 4: "апреля",
            5: "мая", 6: "июня", 7: "июля", 8: "августа",
            9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
        }

        # Форматируем даты с русскими названиями месяцев
        date = f"{birthday_this_year.day:02d} {MONTHS_RU[birthday_this_year.month]}"
        date_before = f"{(birthday_this_year - timedelta(days=1)).day:02d} {MONTHS_RU[(birthday_this_year - timedelta(days=1)).month]}"

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

    # Русские названия месяцев в именительном и родительном падежах
    MONTHS_RU = {
        1: {"nom": "Январь", "gen": "января"},
        2: {"nom": "Февраль", "gen": "февраля"},
        3: {"nom": "Март", "gen": "марта"},
        4: {"nom": "Апрель", "gen": "апреля"},
        5: {"nom": "Май", "gen": "мая"},
        6: {"nom": "Июнь", "gen": "июня"},
        7: {"nom": "Июль", "gen": "июля"},
        8: {"nom": "Август", "gen": "августа"},
        9: {"nom": "Сентябрь", "gen": "сентября"},
        10: {"nom": "Октябрь", "gen": "октября"},
        11: {"nom": "Ноябрь", "gen": "ноября"},
        12: {"nom": "Декабрь", "gen": "декабря"}
    }

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
    allowed_tags = [
        'b', 'strong', 'i', 'em', 'u', 'ins', 's', 'strike', 'del',
        'span', 'tg-spoiler', 'a', 'code', 'pre', 'blockquote',
        'tg-emoji'
    ]
    tag_pattern = re.compile(r'</?([a-z-]+)(?:\s+[^>]*)?>')

    # Находим все HTML-теги в шаблоне
    tags = tag_pattern.findall(template)

    # Проверяем, что все теги разрешены
    return all(tag.lower() in allowed_tags for tag in tags)

def validate_template_variables(template: str) -> Tuple[bool, List[str]]:
    """
    Проверка переменных в шаблоне.
    Возвращает кортеж (is_valid, invalid_vars).
    """
    allowed_vars = [
        "{name}", "{first_name}", "{last_name}", "{date}",
        "{date_before}", "{days_until}", "{phone_pay}", "{name_pay}"
    ]

    # Находим все переменные в шаблоне {variable}
    var_pattern = re.compile(r'\{([^}]+)\}')
    found_vars = var_pattern.findall(template)

    # Проверяем каждую найденную переменную
    invalid_vars = []
    for var in found_vars:
        if "{" + var + "}" not in allowed_vars:
            invalid_vars.append(var)

    return (len(invalid_vars) == 0, invalid_vars)


def get_template_help() -> str:
    """Получение справки по форматированию шаблонов"""
    return """<b>📝 Форматирование шаблонов уведомлений</b>
    
<b>Доступные переменные:</b>
• {name} - Полное имя пользователя (Имя + Фамилия)
• {first_name} - Имя пользователя
• {last_name} - Фамилия пользователя
• {date} - Дата события в формате "ДД месяца"
• {date_before} - Дата за день до события
• {days_until} - Количество дней до события
• {phone_pay} - Номер телефона получателя перевода по СБП (для изменения значения переменной обращайся к @spiderdad)
• {name_pay} - Полное имя получателя перевода по СПБ (для изменения значения переменной обращайся к @spiderdad)
    
<b>HTML-теги для форматирования:</b>
• &lt;b&gt;текст&lt;/b&gt; или &lt;strong&gt;текст&lt;/strong&gt; - <b>Жирный текст</b>
• &lt;i&gt;текст&lt;/i&gt; или &lt;em&gt;текст&lt;/em&gt; - <i>Курсив</i>
• &lt;u&gt;текст&lt;/u&gt; или &lt;ins&gt;текст&lt;/ins&gt; - <u>Подчёркнутый текст</u>
• &lt;s&gt;текст&lt;/s&gt; или &lt;strike&gt;текст&lt;/strike&gt; - <s>Зачёркнутый текст</s>
• &lt;code&gt;текст&lt;/code&gt; - <code>Моноширинный шрифт</code>
• &lt;pre&gt;текст&lt;/pre&gt; - Предварительно отформатированный текст
• &lt;tg-spoiler&gt;текст&lt;/tg-spoiler&gt; - Спойлер
• &lt;blockquote&gt;текст&lt;/blockquote&gt; - Цитата
    
<b>Примеры шаблонов:</b>
1. Современный стиль с эмодзи:
<pre>Коллега, привет! 🎉\n
📅 <b>{name}</b> <b>{date}</b> празднует День Рождения! 🎂\n
Если хочешь принять участие в поздравительном конверте, прошу перевести взнос по номеру телефона <code>{phone_pay}</code> на <b>Альфу</b> или <b>Тинькофф</b> до конца дня <b>{date_before}</b>. Получатель: <i>{name_pay}</i>.\n
⚠️ Пожалуйста, <b>не переводи деньги в другие банки</b>, даже если приложение будет предлагать варианты.\n
В комментарии перевода укажи: <code>ДР {first_name}</code>.\n
Спасибо! 🙌</pre>
    
2. Простой стиль:
<pre>🎂 <b>{date}</b> день рождения у <b>{name}</b>!</pre>
    
3. С запросом на перевод:
<pre>💳 Сбор на подарок\n
Номер: <code>{phone_pay}</code>\n
Получатель: <i>{name_pay}</i>\n
Комментарий: <code>ДР {first_name}</code></pre>
    
<i>Используйте HTML-теги и эмодзи для красивого форматирования ваших уведомлений!"""

def preview_template_message(template: str, previews: List[tuple]) -> str:
    """Форматирование сообщения предварительного просмотра с индикаторами emoji"""
    response = "📝 <b>Предварительный просмотр шаблона</b>\n\n"
    response += "📋 <i>Исходный шаблон:</i>\n"
    response += f"<code>{template}</code>\n\n"
    response += "🔍 <b>Примеры сообщений:</b>\n\n"

    emojis = {
        "today": "📅",
        "tomorrow": "⏰",
        "3days": "📆",
        "week": "📊"
    }

    for preview_type, label, message in previews:
        emoji = emojis.get(preview_type, "🔔")
        response += f"{emoji} <u>{label}:</u>\n{message}\n\n"

    response += "💡 <i>Если шаблон выглядит правильно, используйте /set_template для его сохранения.</i>"
    return response