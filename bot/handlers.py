import telebot
from telebot.handler_backends import State, StatesGroup
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
import os 
import logging
import re # Добавлено для валидации регулярных выражений в set_setting
from collections import defaultdict
import json
from .database import Database
from .notification_manager import NotificationManager
from .message_templates import get_welcome_message, format_birthday_reminder, get_new_user_notification, get_template_help, get_new_user_request_notification
from config import ADMIN_IDS

logger = logging.getLogger(__name__)

# Русские названия месяцев с правильными падежами
MONTHS_RU = {
    1: {'nom': 'Январь', 'gen': 'января'},
    2: {'nom': 'Февраль', 'gen': 'февраля'},
    3: {'nom': 'Март', 'gen': 'марта'},
    4: {'nom': 'Апрель', 'gen': 'апреля'},
    5: {'nom': 'Май', 'gen': 'мая'},
    6: {'nom': 'Июнь', 'gen': 'июня'},
    7: {'nom': 'Июль', 'gen': 'июля'},
    8: {'nom': 'Август', 'gen': 'августа'},
    9: {'nom': 'Сентябрь', 'gen': 'сентября'},
    10: {'nom': 'Октябрь', 'gen': 'октября'},
    11: {'nom': 'Ноябрь', 'gen': 'ноября'},
    12: {'nom': 'Декабрь', 'gen': 'декабря'}
}

class BotHandlers:
    def __init__(self, bot: telebot.TeleBot, db: Database, notification_manager: NotificationManager):
        """Инициализация обработчиков бота"""
        self.bot = bot
        self.db = db
        self.notification_manager = notification_manager
        # Проверяем структуру базы данных
        self.db.check_table_structure()
        # Временное хранилище для пользователей, начавших диалог с ботом
        self.active_users = defaultdict(dict)
        # Списки команд для разных типов пользователей
        self.admin_commands = [
            telebot.types.BotCommand("start", "Запустить бота"),
            telebot.types.BotCommand("birthdays", "Список дней рождения"),
            telebot.types.BotCommand("add_user", "Добавить пользователя"),
            telebot.types.BotCommand("get_users_directory", "Справочник пользователей"),
            telebot.types.BotCommand("remove_user", "Удалить пользователя"),
            telebot.types.BotCommand("set_admin", "Назначить администратора"),
            telebot.types.BotCommand("remove_admin", "Отозвать права администратора"),
            telebot.types.BotCommand("toggle_notifications", "Управление уведомлениями пользователя"),
            telebot.types.BotCommand("force_notify", "Отправить тестовое уведомление"),
            telebot.types.BotCommand("get_templates", "Список шаблонов"),
            telebot.types.BotCommand("set_template", "Добавить шаблон"),
            telebot.types.BotCommand("update_template", "Обновить шаблон"),
            telebot.types.BotCommand("test_template", "Тест шаблона"),
            telebot.types.BotCommand("preview_template", "Предпросмотр шаблона"),
            telebot.types.BotCommand("delete_template", "Удалить шаблон"),
            telebot.types.BotCommand("activate_template", "Активировать шаблон"),
            telebot.types.BotCommand("deactivate_template", "Деактивировать шаблон"),
            telebot.types.BotCommand("create_backup", "Создать резервную копию"),
            telebot.types.BotCommand("list_backups", "Список резервных копий"),
            telebot.types.BotCommand("restore_backup", "Восстановить из копии"),
            telebot.types.BotCommand("get_settings", "Настройки уведомлений"),
            telebot.types.BotCommand("set_setting", "Добавить настройку уведомлений"),
            telebot.types.BotCommand("edit_setting", "Изменить настройку уведомлений"),
            telebot.types.BotCommand("delete_setting", "Удалить настройку уведомлений"),
            telebot.types.BotCommand("help_template", "Помощь по шаблонам"),
            telebot.types.BotCommand("game2048", "Игра 2048")
        ]
        self.user_commands = [
            telebot.types.BotCommand("start", "Запустить бота"),
            telebot.types.BotCommand("birthdays", "Список дней рождения"),
            telebot.types.BotCommand("game2048", "Игра 2048")
        ]

    def register_handlers(self):
        """Регистрация всех обработчиков команд"""
        # Базовые команды (доступны всем)
        self.bot.message_handler(commands=['start'])(self.start)
        self.bot.message_handler(commands=['birthdays'])(self.list_birthdays)
        self.bot.message_handler(commands=['game2048'])(self.game2048)

        # Обработчик подтверждения подписки
        self.bot.message_handler(func=lambda message: message.text.lower() == 'да')(self.handle_subscription_confirmation)

        # Обработчики callback-запросов
        self.bot.callback_query_handler(func=lambda call: call.data == 'birthdays')(self.birthdays_callback)
        
        # Обработчики callback-запросов для групп команд администратора
        self.bot.callback_query_handler(func=lambda call: call.data == 'admin_users')(self.admin_users_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'admin_templates')(self.admin_templates_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'admin_notifications')(self.admin_notifications_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'admin_backup')(self.admin_backup_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'back_to_main')(self.back_to_main_callback)
        
        # Обработчики callback-запросов для команд администратора
        command_callbacks = {
            'cmd_add_user': self.cmd_add_user_callback,
            'cmd_users': self.cmd_users_callback,
            'cmd_remove_user': self.cmd_remove_user_callback,
            'cmd_set_admin': self.cmd_set_admin_callback,
            'cmd_remove_admin': self.cmd_remove_admin_callback,
            'cmd_get_templates': self.cmd_get_templates_callback,
            'cmd_set_template': self.cmd_set_template_callback,
            'cmd_update_template': self.cmd_update_template_callback,
            'cmd_test_template': self.cmd_test_template_callback,
            'cmd_preview_template': self.cmd_preview_template_callback,
            'cmd_delete_template': self.cmd_delete_template_callback,
            'cmd_activate_template': self.cmd_activate_template_callback,
            'cmd_deactivate_template': self.cmd_deactivate_template_callback,
            'cmd_help_template': self.cmd_help_template_callback,
            'cmd_get_settings': self.cmd_get_settings_callback,
            'cmd_toggle_notifications': self.cmd_toggle_notifications_callback,
            'cmd_set_setting': self.cmd_set_setting_callback,
            'cmd_edit_setting': self.cmd_edit_setting_callback,
            'cmd_delete_setting': self.cmd_delete_setting_callback,
            'cmd_force_notify': self.cmd_force_notify_callback,
            'cmd_backup': self.cmd_backup_callback,
            'cmd_list_backups': self.cmd_list_backups_callback,
            'cmd_restore': self.cmd_restore_callback
        }
        
        for command, handler in command_callbacks.items():
            self.bot.callback_query_handler(func=lambda call, cmd=command: call.data == cmd)(handler)

        # Административные команды (требуют проверки прав)
        admin_commands = {
            'add_user': self.add_user,
            'get_users_directory': self.get_users_directory,
            'remove_user': self.remove_user,
            'set_admin': self.set_admin,
            'remove_admin': self.remove_admin,
            'toggle_notifications': self.toggle_notifications,
            'force_notify': self.force_notify,
            'get_templates': self.get_templates,
            'set_template': self.set_template,
            'update_template': self.update_template,
            'delete_template': self.delete_template,
            'test_template': self.test_template,
            'preview_template': self.preview_template,
            'activate_template': self.activate_template,
            'deactivate_template': self.deactivate_template,
            'create_backup': self.create_backup,
            'list_backups': self.list_backups,
            'restore_backup': self.restore_backup,
            'get_settings': self.get_settings,
            'set_setting': self.set_setting,
            'edit_setting': self.edit_setting,
            'delete_setting': self.delete_setting,
            'help_template': self.help_template,
            'game2048': self.game2048
        }

        for command, handler in admin_commands.items():
            self.bot.message_handler(commands=[command])(
                lambda message, h=handler: self._admin_handler(message, h)
            )

    def setup_command_menu(self):
        """Настройка меню команд для пользователей и администраторов"""
        try:
            # Установка базового меню для всех пользователей
            self.bot.delete_my_commands()  # Очищаем текущее меню
            self.bot.set_my_commands(self.user_commands)
            logger.info("Установлено базовое меню команд")

            # Установка расширенного меню для администраторов
            for admin_id in ADMIN_IDS:
                try:
                    # Проверяем, существует ли чат с администратором
                    try:
                        self.bot.get_chat(admin_id)
                    except Exception as chat_error:
                        logger.error(f"Не удалось найти чат с администратором {admin_id}: {str(chat_error)}")
                        continue

                    scope = telebot.types.BotCommandScopeChat(admin_id)

                    # Удаляем старые команды для админа
                    try:
                        self.bot.delete_my_commands(scope=scope)
                        logger.debug(f"Удалены старые команды для администратора {admin_id}")
                    except Exception as del_error:
                        logger.warning(f"Не удалось удалить старые команды для администратора {admin_id}: {str(del_error)}")

                    # Устанавливаем новые команды
                    result = self.bot.set_my_commands(
                        commands=self.admin_commands,
                        scope=scope
                    )

                    if result:
                        logger.info(f"Установлено меню администратора для ID {admin_id}")
                    else:
                        logger.error(f"Не удалось установить меню для администратора {admin_id}")

                except Exception as e:
                    logger.error(f"Ошибка установки меню для администратора {admin_id}: {str(e)}")
                    continue

            logger.info("Меню команд установлено успешно")

        except Exception as e:
            logger.error(f"Ошибка при установке меню команд: {str(e)}")

    def _admin_handler(self, message: telebot.types.Message, handler):
        """Обертка для административных команд с проверкой прав"""
        if message.from_user.id not in ADMIN_IDS:
            self.bot.reply_to(
                message,
                "❌ Эта команда доступна только администраторам бота."
            )
            return
        handler(message)

    def _check_access(self, message: telebot.types.Message) -> bool:
        """Проверка доступа пользователя к командам бота"""
        user_id = message.from_user.id
        command = message.text.split()[0][1:] if message.text.startswith('/') else None

        # Администраторы имеют полный доступ
        if user_id in ADMIN_IDS:
            logger.info(f"Доступ администратора разрешен для пользователя {user_id}")
            return True

        # Для обычных пользователей разрешены только базовые команды
        if command in ['start', 'birthdays']:
            # Проверяем подписку для команды birthdays
            if command == 'birthdays':
                with self.db.get_connection() as conn:
                    user = conn.execute(
                        "SELECT is_subscribed FROM users WHERE telegram_id = ?",
                        (user_id,)
                    ).fetchone()
                    if not user or not user['is_subscribed']:
                        self.bot.reply_to(
                            message,
                            "❌ У тебя нет доступа. Жми /start или подожди, пока администратор добавит тебя."
                        )
                        return False
            return True

        # Для всех остальных команд - запрещаем доступ
        logger.warning(f"Отказано в доступе пользователю {user_id} к команде {command}")
        self.bot.reply_to(
            message,
            "❌ <b>Прости, но эта команда доступна только администратору бота.</b>",
            parse_mode='HTML'
        )
        return False

    def start(self, message: telebot.types.Message):
        """Обработка команды /start"""
        user = message.from_user
        user_id = user.id

        # Сохраняем информацию о пользователе во временное хранилище
        self.active_users[user.username] = {
            'telegram_id': user_id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name
        }

        logger.info(f"Пользователь {user.username} (ID: {user_id}) начал взаимодействие с ботом")

        # Проверяем, является ли пользователь администратором
        is_admin = user_id in ADMIN_IDS

        # Проверяем существование пользователя в базе данных
        with self.db.get_connection() as conn:
            user_record = conn.execute(
                "SELECT telegram_id, is_subscribed FROM users WHERE telegram_id = ?",
                (user_id,)
            ).fetchone()

        # Определяем, авторизован ли пользователь
        is_authorized = user_record is not None

        if not is_authorized:
            # Уведомляем администраторов о новом пользователе
            user_info = {
                'telegram_id': user_id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
            admin_notification = get_new_user_request_notification(user_info)
            for admin_id in ADMIN_IDS:
                try:
                    self.bot.send_message(
                        admin_id,
                        admin_notification,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления администратору {admin_id}: {str(e)}")

            # Отправляем сообщение неавторизованному пользователю
            welcome_message = get_welcome_message(is_admin=is_admin, is_authorized=is_authorized)
            self.bot.reply_to(message, welcome_message, parse_mode='HTML')
            return

        # Создаем клавиатуру в зависимости от роли пользователя
        if is_admin:
            # Приветственное сообщение для администратора
            welcome_text = "Привет! 👋\n\nТы авторизован как Администратор, можешь использовать все возможности бота.\nНиже отображаются доступные команды, сгруппированные по смыслу действий:"
            
            # Создаем клавиатуру для администратора с группами команд
            keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
            
            # Основные команды
            birthdays_button = telebot.types.InlineKeyboardButton(
                text="🎂 Дни рождения",
                callback_data="birthdays"
            )
            game_button = telebot.types.InlineKeyboardButton(
                text="🎮 Игра 2048",
                url="https://t.me/PlayToTime_bot/Game2048"
            )
            
            # Группы команд для администратора
            users_button = telebot.types.InlineKeyboardButton(
                text="👥 Пользователи",
                callback_data="admin_users"
            )
            templates_button = telebot.types.InlineKeyboardButton(
                text="📋 Шаблоны",
                callback_data="admin_templates"
            )
            notifications_button = telebot.types.InlineKeyboardButton(
                text="📢 Рассылки",
                callback_data="admin_notifications"
            )
            backup_button = telebot.types.InlineKeyboardButton(
                text="💾 Резервные копии",
                callback_data="admin_backup"
            )
            
            # Добавляем кнопки в клавиатуру
            keyboard.add(birthdays_button, game_button)
            keyboard.add(users_button, templates_button)
            keyboard.add(notifications_button, backup_button)
        else:
            # Приветственное сообщение для обычного пользователя
            welcome_text = "Привет! 👋\n\nТы авторизован как Пользователь, тебе доступен следующий функционал:"
            
            # Создаем клавиатуру для обычного пользователя
            keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
            
            # Кнопки для пользователя
            birthdays_button = telebot.types.InlineKeyboardButton(
                text="🎂 Дни рождения",
                callback_data="birthdays"
            )
            game_button = telebot.types.InlineKeyboardButton(
                text="🎮 Игра 2048",
                url="https://t.me/PlayToTime_bot/Game2048"
            )
            
            # Добавляем кнопки в клавиатуру
            keyboard.add(birthdays_button, game_button)
        
        # Отправляем сообщение с клавиатурой
        self.bot.send_message(
            message.chat.id,
            welcome_text,
            parse_mode='HTML',
            reply_markup=keyboard
        )

    def list_birthdays(self, message: telebot.types.Message):
        """Обработка команды /birthdays"""
        if not self._check_access(message):
            return

        birthdays = self.db.get_all_birthdays()

        if not birthdays:
            self.bot.reply_to(message, "📝 В базе данных нет дней рождения.")
            return

        # Формируем заголовок
        response = [
            "🎂 <b>Список дней рождения:</b>"
        ]

        # Группируем дни рождения по месяцам
        birthdays_by_month = {}
        for user in birthdays:
            birth_date = datetime.strptime(user['birth_date'], '%Y-%m-%d')
            month = birth_date.month
            if month not in birthdays_by_month:
                birthdays_by_month[month] = []
            birthdays_by_month[month].append((birth_date.day, user))

        # Добавляем месяцы по порядку с правильным форматированием
        for month in sorted(birthdays_by_month.keys()):
            response.append(f"\n📅 <b>{MONTHS_RU[month]['nom']}</b>:")
            # Сортируем по дням внутри каждого месяца
            for day, user in sorted(birthdays_by_month[month]):
                name = f"{user['first_name']}"
                if user['last_name']:
                    name += f" {user['last_name']}"
                response.append(f"👤 <i>{name}</i> - {day:02d} {MONTHS_RU[month]['gen']}")

        self.bot.reply_to(message, "\n".join(response), parse_mode='HTML')

    def add_user(self, message: telebot.types.Message):
        """Handle /add_user command"""
        if message.from_user.id not in ADMIN_IDS:
            self.bot.reply_to(message, "❌ <b>Прости, но эта команда доступна только администратору бота.</b>", parse_mode='HTML')
            return

        try:
            # Expected format: /add_user @username FirstName LastName YYYY-MM-DD
            parts = message.text.split()
            if len(parts) != 5:
                raise ValueError("Invalid command format")

            _, username, first_name, last_name, birth_date = parts
            username = username.lstrip('@')

            # Validate date format
            try:
                datetime.strptime(birth_date, "%Y-%m-%d")
            except ValueError:
                self.bot.reply_to(message, "❌ <b>Неверный формат даты.</b> Используйте YYYY-MM-DD", parse_mode='HTML')
                return

            # # Check if user has started the bot
            # if username not in self.active_users:
            #     self.bot.reply_to(
            #         message,
            #         f"⚠️ <b>Не удалось добавить пользователя @{username}.</b>\n"
            #         "<b>Важно:</b> для добавления пользователя необходимо:\n\n"
            #         f"1. Пользователь должен найти бота @{self.bot.get_me().username}\n"
            #         "2. Нажать кнопку START или отправить команду /start\n"
            #         "3. После этого повторить команду добавления пользователя\n\n"
            #         "❗️ Пожалуйста, попросите пользователя выполнить эти шаги и повторите попытку.",
            #         parse_mode='HTML'
            #     )
            #     return

            # Get user information from storage
            user_info = self.active_users[username]
            telegram_id = user_info['telegram_id']

            # Check if user already exists
            with self.db.get_connection() as conn:
                existing_user = conn.execute(
                    "SELECT * FROM users WHERE telegram_id = ? OR username = ?",
                    (telegram_id, username)
                ).fetchone()

            if existing_user:
                logger.warning(f"User @{username} already exists in database")
                self.bot.reply_to(message, "❌ <b>Пользователь уже существует в базе данных.</b>", parse_mode='HTML')
                return

            # Try to add user to database
            success = self.db.add_user(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                birth_date=birth_date,
                is_subscribed=True
            )

            if success:
                logger.info(f"Successfully added user @{username} to database")

                # Try to send notification to the new user
                try:
                    notification = get_new_user_notification(first_name)
                    sent = self.bot.send_message(telegram_id, notification, parse_mode='HTML')
                    if sent:
                        logger.info(f"Successfully sent notification to user @{username}")
                        self.bot.reply_to(
                            message,
                            f"✅ Пользователь <b>@{username}</b> успешно добавлен и получил уведомление.",
                            parse_mode='HTML'
                        )
                    else:
                        raise telebot.apihelper.ApiException("Failed to send message")
                except telebot.apihelper.ApiException as e:
                    logger.error(f"Failed to send notification to user @{username}: {str(e)}")
                    self.bot.reply_to(
                        message,
                        f"⚠️ Пользователь <b>@{username}</b> добавлен в базу данных, "
                        "но не удалось отправить ему уведомление.\n"
                        "<b>Возможные причины:</b>\n"
                        "1. Пользователь заблокировал бота\n"
                        "2. Проблемы с доступом к API Telegram",
                        parse_mode='HTML'
                    )
            else:
                logger.error(f"Failed to add user @{username} to database")
                self.bot.reply_to(message, "❌ <b>Ошибка при добавлении пользователя в базу данных.</b>", parse_mode='HTML')

        except ValueError as e:
            logger.error(f"Invalid command format: {str(e)}")
            self.bot.reply_to(
                message,
                "❌ <b>Неверный формат команды.</b> Используйте:\n"
                "<code>/add_user @username FirstName LastName YYYY-MM-DD</code>",
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Unexpected error while adding user: {str(e)}")
            self.bot.reply_to(
                message,
                "❌ <b>Произошла неожиданная ошибка.</b> Пожалуйста, попробуйте позже.",
                parse_mode='HTML'
            )

    def handle_subscription_confirmation(self, message: telebot.types.Message):
        """Обработка подтверждения подписки от пользователей"""
        user_id = message.from_user.id

        with self.db.get_connection() as conn:
            user = conn.execute(
                "SELECT telegram_id, is_subscribed, first_name, last_name, username FROM users WHERE telegram_id = ?",
                (user_id,)
            ).fetchone()

        if not user:
            logger.warning(f"Попытка подтверждения подписки от неизвестного пользователя: {user_id}")
            self.bot.reply_to(
                message,
                "❌ <b>Вы не были добавлены в систему.</b> Обратитесь к администратору бота.",
                parse_mode='HTML'
            )
            return

        is_subscribed = bool(user['is_subscribed'])
        logger.info(f"Обработка подтверждения подписки для пользователя {user_id}, текущий статус: {is_subscribed}")

        if not is_subscribed:
            if self.db.update_user(user_id, is_subscribed=True):
                logger.info(f"Пользователь {user_id} успешно подписался на уведомления")

                # Отправляем подтверждение пользователю
                self.bot.reply_to(
                    message,
                    "✅ <b>Спасибо!</b> Вы успешно подписались на уведомления о днях рождения.",
                    reply_markup=telebot.types.ReplyKeyboardRemove(),
                    parse_mode='HTML'
                )

                # Форматируем имя пользователя для уведомления
                user_name = f"{user['first_name']}"
                if user['last_name']:
                    user_name += f" {user['last_name']}"
                if user['username']:
                    user_name += f" (@{user['username']})"

                # Отправляем уведомление администраторам
                admin_notification = (
                    "✨ <b>Новая подписка на уведомления!</b>\n"
                    f"👤 <b>Пользователь:</b> {user_name}\n"
                    f"🆔 <b>ID:</b> {user_id}"
                )

                for admin_id in ADMIN_IDS:
                    try:
                        self.bot.send_message(
                            admin_id,
                            admin_notification,
                            parse_mode='HTML'
                        )
                        logger.info(f"Отправлено уведомление о подписке администратору {admin_id}")
                    except Exception as e:
                        logger.error(f"Не удалось отправить уведомление администратору {admin_id}: {str(e)}")

            else:
                logger.error(f"Не удалось обновить статус подписки для пользователя {user_id}")
                self.bot.reply_to(
                    message,
                    "❌ <b>Произошла ошибка при подтверждении подписки.</b>\n"
                    "Попробуйте позже или обратитесь к администратору.",
                    parse_mode='HTML'
                )
        else:
            logger.info(f"Пользователь {user_id} уже подписан, игнорируем подтверждение")
            self.bot.reply_to(
                message,
                "ℹ️ <b>Вы уже подписаны на уведомления.</b>",
                reply_markup=telebot.types.ReplyKeyboardRemove(),
                parse_mode='HTML'
            )

    def remove_user(self, message: telebot.types.Message):
        """Handle /remove_user command"""
        if not self._check_access(message):
            return

        try:
            _, username = message.text.split()
            username = username.lstrip('@')

            # Find user by username in database
            with self.db.get_connection() as conn:
                user = conn.execute(
                    "SELECT * FROM users WHERE username = ?",
                    (username,)
                ).fetchone()

            if user and self.db.delete_user(user["telegram_id"]):
                self.bot.reply_to(message, f"✅ Пользователь <b>@{username}</b> успешно удален.", parse_mode='HTML')

                # Notify user about removal if possible
                if user["telegram_id"]:
                    try:
                        self.bot.send_message(
                            chat_id=user["telegram_id"],
                            text="❌ Вы были удалены из системы напоминаний о днях рождения.",
                            parse_mode='HTML'
                        )
                    except Exception:
                        pass
            else:
                self.bot.reply_to(message, "❌ <b>Пользователь не найден.</b>", parse_mode='HTML')

        except ValueError:
            self.bot.reply_to(
                message,
                "❌ <b>Неверный формат команды.</b>\nИспользуйте: /remove_user @username",
                parse_mode='HTML'
            )

    def force_notify(self, message: telebot.types.Message):
        """Обработка команды /force_notify"""
        if not self._check_access(message):
            return

        try:
            # Разбираем команду на части
            parts = message.text.split()
            if len(parts) < 2:
                self.bot.reply_to(
                    message,
                    "❌ Неверный формат команды.\nИспользуйте:\n"
                    "/force_notify @username [текст сообщения]\n\n"
                    "Поддерживаются HTML-теги и эмодзи:\n"
                    "• <b>Жирный текст</b> ✨\n"
                    "• <i>Курсив</i> 🎨\n"
                    "• <code>Моноширинный шрифт</code> 💻\n"
                    "• 🎉 👋 ⚠️ 🎨 и другие эмодзи ✨\n\n"
                    "Подробнее о форматировании: /help_template",
                    parse_mode='HTML'
                )
                return

            # Получаем username и опциональный текст
            username = parts[1].lstrip('@')
            custom_text = ' '.join(parts[2:]) if len(parts) > 2 else None

            # Находим пользователя по username в базе данных
            with self.db.get_connection() as conn:
                user = conn.execute(
                    "SELECT * FROM users WHERE username = ?",
                    (username,)
                ).fetchone()

            if user:
                if custom_text:
                    # Если указан пользовательский текст, проверяем HTML-теги
                    if not validate_template_html(custom_text):
                        self.bot.reply_to(
                            message,
                            "❌ Обнаружены неподдерживаемые HTML-теги. Разрешены теги:\n"
                            "Поддерживаются HTML-теги и эмодзи:\n"
                            "• <b>Жирный текст</b> ✨\n"
                            "• <i>Курсив</i> 🎨\n"
                            "• <code>Моноширинный шрифт</code> 💻\n"
                            "• 🎉 👋 ⚠️ 🎨 и другие эмодзи ✨\n\n"
                            "Подробнее о форматировании: /help_template",
                            parse_mode='HTML'
                        )
                        return

                    # Отправляем пользовательский текст с поддержкой HTML
                    success = self.notification_manager.force_send_notification(
                        user["telegram_id"],
                        f"<b>Сообщение от администратора:</b>\n\n{custom_text}",
                        parse_mode='HTML'
                    )
                else:
                    # Если текст не указан, отправляем тестовое сообщение
                    success = self.notification_manager.force_send_notification(
                        user["telegram_id"],
                        "<b>Тестовое уведомление</b> от администратора 📝\n\n"
                        "Поддерживаются HTML-теги и эмодзи:\n"
                        "• <b>Жирный текст</b> ✨\n"
                        "• <i>Курсив</i> 🎨\n"
                        "• <code>Моноширинный шрифт</code> 💻\n"
                        "• Эмодзи 🎉 👋 ⚠️ 🎨 ✨\n\n"
                        "Подробнее о форматировании: /help_template",
                        parse_mode='HTML'
                    )

                if success:
                    self.bot.reply_to(
                        message,
                        f"✅ Уведомление отправлено пользователю @{username}",
                        parse_mode='HTML'
                    )
                else:
                    self.bot.reply_to(
                        message,
                        f"❌ Ошибка отправки уведомления пользователю @{username}",
                        parse_mode='HTML'
                    )
            else:
                self.bot.reply_to(
                    message,
                    f"❌ Пользователь @{username} не найден",
                    parse_mode='HTML'
                )

        except ValueError as e:
            self.bot.reply_to(
                message,
                "❌ Неверный формат команды.\nИспользуйте:\n"
                "/force_notify @username [текст сообщения]",
                parse_mode='HTML'
            )

    def create_backup(self, message: telebot.types.Message):
        """Handle /backup command"""
        if not self._check_access(message):
            return

        backup_path = self.db.create_backup()
        if backup_path:
            backup_name = os.path.basename(backup_path)
            self.bot.reply_to(
                message, 
                f"✅ Резервная копия создана успешно: {backup_name}"
            )
        else:
            self.bot.reply_to(
                message, 
                "❌ Ошибка при создании резервной копии. Проверьте логи."
            )

    def list_backups(self, message: telebot.types.Message):
        """Handle /list_backups command"""
        if not self._check_access(message):
            return

        backups = self.db.list_backups()
        if backups:
            backup_list = "\n".join(f"📁 {backup}" for backup in backups)
            self.bot.reply_to(
                message,
                f"Доступные резервные копии:\n\n{backup_list}"
            )
        else:
            self.bot.reply_to(message, "Резервных копий не найдено.")

    def restore_backup(self, message: telebot.types.Message):
        """Handle /restore command"""
        if not self._check_access(message):
            return

        try:
            _, backup_name = message.text.split(maxsplit=1)
            backup_path = os.path.join(self.db.backup_dir, backup_name)

            if self.db.restore_from_backup(backup_path):
                self.bot.reply_to(
                    message,
                    f"✅ База данных успешно восстановлена из копии: {backup_name}"
                )
            else:
                self.bot.reply_to(
                    message,
                    "❌ Ошибка при восстановлении базы данных. Проверьте логи."
                )

        except ValueError:
            self.bot.reply_to(
                message,
                "Неверный формат команды. Используйте: /restore <имя_файла_копии>"
            )

    def get_templates(self, message: telebot.types.Message):
        """Get list of notification templates"""
        if not self._check_access(message):
            return

        templates = self.db.get_templates()
        if not templates:
            self.bot.reply_to(message, "📝 <b>Шаблоны не найдены.</b>", parse_mode='HTML')
            return

        for template in templates:
            response = [
                f"📋 <b>Шаблон #{template['id']}</b>",
                f"📌 <b>Название:</b> {template['name']}",
                f"📝 <b>Текст:</b>\n{template['template']}",
                f"📂 <b>Категория:</b> {template['category']}",
                f"🕒 <b>Создан:</b> {template['created_at']}"
            ]

            if template['updated_at'] and template['updated_at'] != template['created_at']:
                response.append(f"✏️ <b>Изменён:</b> {template['updated_at']}")

            status = "✅ Активен" if template['is_active'] else "❌ Неактивен"
            response.append(f"📊 <b>Статус:</b> {status}")

            # Add notification settings if they exist
            settings = template.get('settings', [])
            if settings:
                response.append("\n📅 <b>Настройки уведомлений:</b>")
                for setting in settings:
                    if isinstance(setting, dict):
                        active_emoji = "✅" if setting.get('is_active', False) else "❌"
                        response.append(f"{active_emoji} За {setting['days_before']} дней в {setting['time']}")
            else:
                response.append("\n⚠️ Нет активных настроек уведомлений")

            self.bot.reply_to(message, "\n".join(response), parse_mode='HTML')


    def _validate_template(self, template: str) -> Tuple[bool, str]:
        """Validate template variables and HTML tags
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        # Check HTML tags
        if not validate_template_html(template):
            return False, (
                "❌ <b>Обнаружены недопустимые HTML-теги.</b>\n"
                "Разрешены теги:\n"
                "• &lt;b&gt; для жирного текста\n"
                "• &lt;i&gt; для курсива\n"
                "• &lt;code&gt; для моноширинного шрифта\n\n"
                "Используйте /help_template для справки."
            )

        # Check template variables
        allowed_vars = ["{name}", "{first_name}", "{last_name}", "{date}", 
                       "{date_before}", "{days_until}", "{phone_pay}", "{name_pay}"]

        # Find all variables in template using regex
        found_vars = re.findall(r'{[^}]+}', template)
        invalid_vars = [var for var in found_vars if var not in allowed_vars]

        if invalid_vars:
            return False, (                "❌ <b>Обнаружены недопустимые переменные:</b>\n"
                f"{', '.join(invalid_vars)}\n\n"
                "<b>Разрешены переменные:</b>\n"
                "• {name} - полное имя\n"
                "• {first_name} - имя\n"
                "• {last_name} - фамилия\n"
                "• {date} - дата события\n"
                "• {date_before} - дата напоминания\n"
                "• {days_until} - дней до события\n"
                "• {phone_pay} - телефон плательщика\n"
                "• {name_pay} - имя плательщика\n\n"
                "Используйте /help_template для справки."
            )

        return True, ""

    def set_template(self, message: telebot.types.Message):
        """Add new notification template"""
        if not self._check_access(message):
            return

        try:
            # Format: /set_template name category text
            parts = message.text.split(maxsplit=3)
            if len(parts) != 4:
                self.bot.reply_to(
                    message,
                    "❌ <b>Неверный формат команды.</b>\n"
                    "Используйте: /set_template название категория текст_шаблона",
                    parse_mode='HTML'
                )
                return

            _, name, category, template = parts

            # Validate template
            is_valid, error_msg = self._validate_template(template)
            if not is_valid:
                self.bot.reply_to(message, error_msg, parse_mode='HTML')
                return

            success = self.db.add_notification_template(name, template, category)
            if success:
                self.bot.reply_to(
                    message,
                    "✅ <b>Шаблон успешно добавлен.</b>",
                    parse_mode='HTML'
                )
            else:
                self.bot.reply_to(
                    message,
                    "❌ <b>Ошибка при добавлении шаблона.</b>",
                    parse_mode='HTML'
                )

        except Exception as e:
            logger.error(f"Error adding template: {str(e)}")
            self.bot.reply_to(
                message,
                "❌ <b>Произошла ошибка при добавлении шаблона.</b>",
                parse_mode='HTML'
            )

    def update_template(self, message: telebot.types.Message):
        """Update existing notification template"""
        if not self._check_access(message):
            return

        try:
            # Expected format: /update_template template_id new text here
            parts = message.text.split()
            if len(parts) < 3:
                self.bot.reply_to(
                    message,
                    "❌ <b>Неверный формат команды.</b>\n"
                    "Используйте: /update_template ID текст_шаблона",
                    parse_mode='HTML'
                )
                return

            template_id = int(parts[1])
            new_template = ' '.join(parts[2:])

            # Validate template
            is_valid, error_msg = self._validate_template(new_template)
            if not is_valid:
                self.bot.reply_to(message, error_msg, parse_mode='HTML')
                return

            # Update template
            success, msg = self.db.update_notification_template(
                template_id=template_id,
                template=new_template
            )

            if success:
                self.bot.reply_to(
                    message,
                    f"✅ <b>{msg}</b>",
                    parse_mode='HTML'
                )
            else:
                self.bot.reply_to(
                    message,
                    f"❌ <b>{msg}</b>",
                    parse_mode='HTML'
                )

        except ValueError:
            self.bot.reply_to(
                message,
                "❌ <b>Неверный ID шаблона.</b>\n"
                "ID должен быть числом.",
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error updating template: {str(e)}")
            self.bot.reply_to(
                message,
                "❌ <b>Произошла ошибка при обновлении шаблона.</b>",
                parse_mode='HTML'
            )

    def preview_template(self, message: telebot.types.Message):
        """Preview template with sample data"""
        if not self._check_access(message):
            return

        try:
            # Format: /preview_template template_text
            parts = message.text.split(maxsplit=1)
            if len(parts) != 2:
                self.bot.reply_to(
                    message,
                    "❌ <b>Неверный формат команды.</b>\n"
                    "Используйте: /preview_template текст_шаблона",
                    parse_mode='HTML'
                )
                return

            template = parts[1]

            # Validate template
            is_valid, error_msg = self._validate_template(template)
            if not is_valid:
                self.bot.reply_to(message, error_msg, parse_mode='HTML')
                return

            # Sample data for preview
            sample_data = {
                'name': 'Иван Петров',
                'first_name': 'Иван',
                'last_name': 'Петров',
                'date': '01.01.2024',
                'date_before': '25.12.2023',
                'days_until': '7',
                'phone_pay': '+7 (999) 123-45-67',
                'name_pay': 'Анна Петрова'
            }

            # Replace variables
            preview = template
            for var, value in sample_data.items():
                preview = preview.replace(f"{{{var}}}", value)

            response = [
                "📱 <b>Предпросмотр шаблона</b>\n",
                "Так будет выглядеть сообщение:\n",
                "➖➖➖➖➖➖➖➖➖➖",
                preview,
                "➖➖➖➖➖➖➖➖➖➖"
            ]

            self.bot.reply_to(
                message,
                "\n".join(response),
                parse_mode='HTML'
            )

        except Exception as e:
            logger.error(f"Error previewing template: {str(e)}")
            self.bot.reply_to(
                message,
                "❌ <b>Произошла ошибка при предпросмотре шаблона.</b>",
                parse_mode='HTML'
            )

    def delete_template(self, message: telebot.types.Message):
        """Delete notification template"""
        if not self._check_access(message):
            return

        try:
            # Expected format: /delete_template template_id
            parts = message.text.split()
            if len(parts) != 2:
                self.bot.reply_to(
                    message,
                    "❌ <b>Неверный формат команды.</b>\n"
                    "Используйте: /delete_template ID",
                    parse_mode='HTML'
                )
                return

            template_id = int(parts[1])
            success, msg = self.db.delete_notification_template(template_id)

            self.bot.reply_to(message, f"<b>{msg}</b>", parse_mode='HTML')

        except ValueError:
            self.bot.reply_to(
                message,
                "❌ <b>Неверный ID шаблона.</b>\n"
                "ID должен быть числом.",
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error deleting template: {str(e)}")
            self.bot.reply_to(
                message,
                "❌ <b>Произошла ошибка при удалении шаблона.</b>",
                parse_mode='HTML'
            )

    def get_settings(self, message: telebot.types.Message):
        """Handle /get_settings command"""
        if not self._check_access(message):
            return

        settings = self.db.get_notification_settings()
        if not settings:
            self.bot.reply_to(message, "⚙️ Настройки уведомлений не найдены.")
            return

        response = "⚙️ Текущие настройки уведомлений:\n\n"
        for setting in settings:
            response += f"ID: {setting['id']}\n"
            response += f"Шаблон: {setting['template_name']}\n"
            response += f"За {setting['days_before']} дней, время: {setting['time']}\n"
            response += f"Статус: {'Активен' if setting['is_active'] else 'Неактивен'}\n\n"

        self.bot.reply_to(message, response)

    def set_setting(self, message: telebot.types.Message):
        """Добавление новой настройки уведомлений
        Формат: /set_setting <template_id> <days_before> <time>
        Пример: /set_setting 1 3 10:00
        """
        if not self._check_access(message):
            return

        try:
            parts = message.text.split()
            if len(parts) != 4:
                raise ValueError("Неверное количество параметров")

            template_id = int(parts[1])
            days_before = int(parts[2])
            time = parts[3]

            # Проверяем формат времени
            if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', time):
                raise ValueError("Неверный формат времени. Используйте HH:MM")

            success, new_id, msg = self.db.add_notification_setting(template_id, days_before, time)

            if success:
                # Перезагружаем настройки уведомлений
                self.notification_manager.reload_settings()
                self.bot.reply_to(message, f"✅ {msg}\nID новой настройки: {new_id}")
            else:
                self.bot.reply_to(message, f"❌ {msg}")

        except ValueError as e:
            self.bot.reply_to(
                message,
                f"❌ Ошибка: {str(e)}\n\n"
                "Правильный формат:\n"
                "/set_setting <template_id> <days_before> <time>\n"
                "Пример: /set_setting 1 3 10:00"
            )
        except Exception as e:
            logger.error(f"Error in set_setting: {str(e)}")
            self.bot.reply_to(
                message,
                "❌ Произошла ошибка при добавлении настройки уведомлений"
            )

    def edit_setting(self, message: telebot.types.Message):
        """Handle /edit_setting command"""
        if not self._check_access(message):
            return

        try:
            # Expected format: /edit_setting <setting_id> <days_before> <time>
            parts = message.text.split()
            if len(parts) != 4:
                self.bot.reply_to(
                    message,
                    "❌ Неверный формат команды. Используйте:\n"
                    "/edit_setting <setting_id> <days_before> <time>\n"
                    "Пример: /edit_setting 1 3 10:00"
                )
                return

            _, setting_id, days_before, time = parts
            setting_id = int(setting_id)
            days_before = int(days_before)

            # Validate time format (HH:MM)
            if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', time):
                self.bot.reply_to(
                    message,
                    "❌ Неверный формат времени. Используйте формат HH:MM (например, 10:00)"
                )
                return

            # Update notification setting
            success, error_message = self.db.update_notification_setting(
                setting_id=setting_id,
                days_before=days_before,
                time=time
            )

            if success:
                # Reload notification settings after update
                self.notification_manager.reload_settings()
                self.bot.reply_to(
                    message,
                    f"✅ Настройка #{setting_id} успешно обновлена:\n"
                    f"• За {days_before} дней в {time}"
                )
                logger.info(f"Successfully updated notification setting #{setting_id}")
            else:
                self.bot.reply_to(message, f"❌ {error_message}")
                logger.error(f"Failed to update setting #{setting_id}: {error_message}")

        except ValueError as e:
            logger.error(f"Invalid parameter in edit_setting: {str(e)}")
            self.bot.reply_to(
                message,
                "❌ Ошибка в параметрах команды. Убедитесь, что ID настройки и количество дней - это числа."
            )
        except Exception as e:
            logger.error(f"Error in edit_setting: {str(e)}")
            self.bot.reply_to(
                message,
                "❌ Произошла ошибка при обновлении настройки. Проверьте параметры и попробуйте снова."
            )

    def delete_setting(self, message: telebot.types.Message):
        """Удаление настройки уведомлений
        Формат: /delete_setting <setting_id>
        Пример: /delete_setting 1
        """
        if not self._check_access(message):
            return

        try:
            parts = message.text.split()
            if len(parts) != 2:
                raise ValueError("Неверное количество параметров")

            setting_id = int(parts[1])
            success, msg = self.db.delete_notification_setting(setting_id)

            if success:
                # Перезагружаем настройки уведомлений
                self.notification_manager.reload_settings()
                self.bot.reply_to(message, f"✅ {msg}")
            else:
                self.bot.reply_to(message, f"❌ {msg}")

        except ValueError as e:
            self.bot.reply_to(
                message,
                f"❌ Ошибка: {str(e)}\n\n"
                "Правильный формат:\n"
                "/delete_setting <setting_id>\n"
                "Пример: /delete_setting 1"
            )
        except Exception as e:
            logger.error(f"Error in delete_setting: {str(e)}")
            self.bot.reply_to(
                message,
                "❌ Произошла ошибка при удалении настройки уведомлений"
            )

    def preview_template_message(self, template: str, previews: List[tuple]) -> str:
        """Format preview message with emoji indicators"""
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

    def set_admin(self, message: telebot.types.Message):
        """Handle /set_admin command"""
        if not self._check_access(message):
            return

        try:
            _, username = message.text.split()
            username = username.lstrip('@').lower()  # Convert to lowercase

            logger.info(f"Attempting to set admin rights for username: {username}")

            # Находим пользователя по username (case-insensitive)
            with self.db.get_connection() as conn:
                user = conn.execute("""
                    SELECT * FROM users 
                    WHERE LOWER(username) = LOWER(?)
                """, (username,)).fetchone()

            if not user:
                logger.warning(f"User not found for username: {username}")
                self.bot.reply_to(message, "❌ Пользователь не найден.")
                return

            # Проверяем текущий статус
            if user['is_admin']:
                self.bot.reply_to(message, f"ℹ️ Пользователь @{username} уже является администратором.")
                return

            # Назначаем права администратора
            if self.db.update_user_admin_status(user['telegram_id'], True):
                logger.info(f"Successfully granted admin rights to user {username} (ID: {user['telegram_id']})")
                self.bot.reply_to(message, f"✅ Пользователю @{username} выданы права администратора.")

                # Уведомляем пользователя о получении прав
                try:
                    self.bot.send_message(
                        user['telegram_id'],
                        "🎉 Вам были выданы права администратора в системе Birthday Bot."
                    )
                except Exception as e:
                    logger.error(f"Failed to send notification to new admin: {str(e)}")
            else:
                logger.error(f"Failed to update admin status for user {username}")
                self.bot.reply_to(message, "❌ Ошибка при назначении прав администратора.")

        except ValueError:
            self.bot.reply_to(
                message,
                "❌ Неверный формат команды. Используйте: /set_admin @username"
            )
        except Exception as e:
            logger.error(f"Error in set_admin: {str(e)}")
            self.bot.reply_to(message, "❌ Произошла ошибка при выполнении команды.")

    def remove_admin(self, message: telebot.types.Message):
        """Handle /remove_admin command"""
        if not self._check_access(message):
            return

        try:
            _, username = message.text.split()
            username = username.lstrip('@').lower()  # Convert to lowercase

            logger.info(f"Attempting to remove admin rights from username: {username}")

            # Находим пользователя по username (case-insensitive)
            with self.db.get_connection() as conn:
                user = conn.execute("""
                    SELECT * FROM users 
                    WHERE LOWER(username) = LOWER(?)
                """, (username,)).fetchone()

            if not user:
                logger.warning(f"User not found for username: {username}")
                self.bot.reply_to(message, "❌ Пользователь не найден.")
                return

            # Проверяем текущий статус
            if not user['is_admin']:
                self.bot.reply_to(message, f"ℹ️ Пользователь @{username} не является администратором.")
                return

            # Отзываем права администратора
            if self.db.update_user_admin_status(user['telegram_id'], False):
                logger.info(f"Successfully removed admin rights from user {username} (ID: {user['telegram_id']})")
                self.bot.reply_to(message, f"✅ У пользователя @{username} отозваны права администратора.")

                # Уведомляем пользователя об отзыве прав
                try:
                    self.bot.send_message(
                        user['telegram_id'],
                        "ℹ️ Ваши права администратора в системе Birthday Bot были отозваны."
                    )
                except Exception as e:
                    logger.error(f"Failed to send notification to former admin: {str(e)}")
            else:
                logger.error(f"Failed to update admin status for user {username}")
                self.bot.reply_to(message, "❌ Ошибка при отзыве прав администратора.")

        except ValueError:
            self.bot.reply_to(
                message,
                "❌ Неверный формат команды. Используйте: /remove_admin @username"
            )
        except Exception as e:
            logger.error(f"Error in remove_admin: {str(e)}")
            self.bot.reply_to(message, "❌ Произошла ошибка при выполнении команды.")

    def toggle_notifications(self, message: telebot.types.Message):
        """Переключение статуса уведомлений для пользователя"""
        if not self._check_access(message):
            return

        try:
            # Ожидаемый формат: /toggle_notifications @username
            _, username = message.text.split()
            username = username.lstrip('@')

            # Поиск пользователя в базе данных
            with self.db.get_connection() as conn:
                user = conn.execute(
                    "SELECT * FROM users WHERE username = ?",
                    (username,)
                ).fetchone()

                if not user:
                    self.bot.reply_to(
                        message,
                        "❌ <b>Пользователь не найден.</b>",
                        parse_mode='HTML'
                    )
                    return

                # Инвертируем текущее состояние
                new_status = not bool(user['is_notifications_enabled'])

                # Обновляем статус в базе данных
                conn.execute(
                    "UPDATE users SET is_notifications_enabled = ? WHERE username = ?",
                    (new_status, username)
                )
                conn.commit()

                # Формируем сообщение о результате
                status_text = "включены ✅" if new_status else "отключены ❌"
                self.bot.reply_to(
                    message,
                    f"<b>Уведомления для пользователя @{username} {status_text}</b>",
                    parse_mode='HTML'
                )

                # Отправляем уведомление пользователю
                try:
                    status_msg = (
                        "✅ <b>Уведомления включены!</b>\n\n"
                        "Теперь вы будете получать напоминания о днях рождения."
                    ) if new_status else (
                        "❌ <b>Уведомления отключены.</b>\n\n"
                        "Вы больше не будете получать напоминания о днях рождения.\n"
                        "Чтобы включить их снова, обратитесь к администратору."
                    )

                    self.bot.send_message(
                        chat_id=user['telegram_id'],
                        text=status_msg,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления пользователю {username}: {str(e)}")

        except ValueError:
            self.bot.reply_to(
                message,
                "❌ <b>Неверный формат команды.</b>\nИспользуйте: /toggle_notifications @username",
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Ошибка в toggle_notifications: {str(e)}")
            self.bot.reply_to(
                message,
                "❌ <b>Произошла ошибка при обработке команды.</b>",
                parse_mode='HTML'
            )

    def help_template(self, message: telebot.types.Message):
        """Handle /help_template command"""
        if not self._check_access(message):
            return

        help_message = get_template_help()
        self.bot.reply_to(message, help_message, parse_mode='HTML')

    def preview_template(self, message: telebot.types.Message):
        """Handle /preview_template command"""
        if not self._check_access(message):
            return

        try:
            # Format: /preview_template <template_text>
            cmd_parts = message.text.split(maxsplit=1)
            if len(cmd_parts) != 2:
                raise ValueError()

            template = cmd_parts[1]

            # Validate template
            if not self._validate_template(template):
                self.bot.reply_to(
                    message,
                    "❌ Ошибка: шаблон должен содержать только доступные переменные.\n\n" 
                    "Доступные переменные: {name}, {first_name}, {last_name}, {date}, {date_before}, {days_until}, {phone_pay}, {name_pay}\n"
                    "Используйте /help_template для подробной информации."
                )
                return

            # Test data for preview
            test_data = [
                ("Иван Иванов", "1990-01-15"),
                ("Мария Петрова","1985-03-20"),
                ("Админ Тестовый", "1995-07-10")
            ]

            # Generate preview messages
            previews = []
            for name, birth_date in test_data:
                preview_date = datetime.strptime(birth_date, "%Y-%m-%d")
                msg = template.replace("{name}", name)
                msg = msg.replace("{date}", preview_date.strftime("%d.%m.%Y"))
                previews.append((name, birth_date, msg))

            # Format and send response
            response = self.preview_template_message(template, previews)
            self.bot.reply_to(message, response, parse_mode='HTML')

        except ValueError:
            self.bot.reply_to(
                message,
                "Неверный формат команды. Используйте:\n"
                "/preview_template <текст_шаблона>"
            )

    def get_users_directory(self, message: telebot.types.Message):
        """Handle /users command - display users directory"""
        if not self._check_access(message):
            return

        try:
            # Get all users from database
            with self.db.get_connection() as conn:
                users = conn.execute("""
                    SELECT telegram_id, username, first_name, last_name, 
                           birth_date, is_admin, is_subscribed, is_notifications_enabled
                    FROM users
                    ORDER BY is_admin DESC, is_subscribed DESC, first_name, last_name
                """).fetchall()

            if not users:
                self.bot.reply_to(message, "📝 В базе данных нет пользователей.")
                return

            # Format header
            response = [
                "📒 Справочник пользователей",
                "",
                "Список всех пользователей в системе:"
            ]

            # Group users by role (admin/user)
            admins = []
            regular_users = []

            for user in users:
                # Format birth date
                birth_date = datetime.strptime(user['birth_date'], '%Y-%m-%d')
                date_str = birth_date.strftime('%d.%m.%Y')

                # Build user info string
                user_info = (
                    f"👤 {user['first_name']} {user['last_name']}\n"
                    f"• {'@' + user['username'] if user['username'] else 'Нет username'}\n"
                    f"• 📅 {date_str}\n"
                    f"• Подписка: {'✅' if user['is_subscribed'] else '❌'}\n"
                    f"• Рассылка: {'✅' if user['is_notifications_enabled'] else '❌'}\n"
                    f"• Telegram ID: {user['telegram_id']}"
                )

                if user['is_admin']:
                    admins.append(user_info)
                else:
                    regular_users.append(user_info)

            # Add administrators section
            if admins:
                response.append("\n👑 Администраторы:")
                response.extend(admins)

            # Add regular users section
            if regular_users:
                response.append("\n👥 Пользователи:")
                response.extend(regular_users)

            # Send the formatted message
            self.bot.reply_to(message, "\n\n".join(response))
            logger.info(f"Users directory sent to admin {message.from_user.id}")

        except Exception as e:
            logger.error(f"Error in get_users_directory: {str(e)}")
            self.bot.reply_to(
                message,
                "❌ Произошла ошибка при получении справочника пользователей."
            )

    def activate_template(self, message: telebot.types.Message):
        """Handle /activate_template command"""
        if not self._check_access(message):
            return

        try:
            _, template_id = message.text.split()
            template_id = int(template_id)

            if self.db.update_template_status(template_id, True):
                self.bot.reply_to(
                    message,
                    f"✅ Шаблон #{template_id} успешно активирован."
                )
            else:
                self.bot.reply_to(
                    message,
                    "❌ Не удалось активировать шаблон. Проверьте ID и попробуйте снова."
                )

        except ValueError:
            self.bot.reply_to(
                message,
                "❌ Неверный формат команды. Используйте: /activate_template ID"
            )
        except Exception as e:
            logger.error(f"Error in activate_template: {str(e)}")
            self.bot.reply_to(message, "❌ Произошла ошибка при активации шаблона.")

    def deactivate_template(self, message: telebot.types.Message):
        """Handle /deactivate_template command"""
        if not self._check_access(message):
            return

        try:
            _, template_id = message.text.split()
            template_id = int(template_id)

            if self.db.update_template_status(template_id, False):
                self.bot.reply_to(
                    message,
                    f"✅ Шаблон #{template_id} успешно деактивирован."
                )
            else:
                self.bot.reply_to(
                    message,
                    "❌ Не удалось деактивировать шаблон. Проверьте ID и попробуйте снова."
                )

        except ValueError:
            self.bot.reply_to(
                message,
                "❌ Неверный формат команды. Используйте: /deactivate_template ID"
            )
        except Exception as e:
            logger.error(f"Error in deactivate_template: {str(e)}")
            self.bot.reply_to(message, "❌ Произошла ошибка при деактивации шаблона.")

    def test_template(self, message: telebot.types.Message):
        """Test template with sample data"""
        if not self._check_access(message):
            return

        try:
            # Format: /test_template <template_id> <test_name>
            parts = message.text.split()
            if len(parts) < 3:
                self.bot.reply_to(
                    message,
                    "❌ <b>Неверный формат команды.</b>\n"
                    "Используйте: /test_template ID тестовое_имя",
                    parse_mode='HTML'
                )
                return

            template_id = int(parts[1])
            test_name = ' '.join(parts[2:])

            # Get template from database
            with self.db.get_connection() as conn:
                template = conn.execute("""
                    SELECT * FROM notification_templates
                    WHERE id = ?
                """, (template_id,)).fetchone()

            if not template:
                self.bot.reply_to(
                    message,
                    "❌ <b>Шаблон не найден.</b>",
                    parse_mode='HTML'
                )
                return

            # Validate template
            is_valid, error_msg = self._validate_template(template['template'])
            if not is_valid:
                self.bot.reply_to(message, error_msg, parse_mode='HTML')
                return

            # Test dates
            test_dates = [
                datetime.now(),
                datetime.now() + timedelta(days=1),
                datetime.now() + timedelta(days=7)
            ]

            # Sample data for testing
            sample_data = {
                'name': test_name,
                'first_name': test_name.split()[0],
                'last_name': test_name.split()[1] if len(test_name.split()) > 1 else '',
                'phone_pay': os.getenv('PHONE_PAY', ''),
                'name_pay': os.getenv('NAME_PAY', '')
            }

            response = [
                f"📱 <b>Тест шаблона #{template_id}</b>",
                f"📝 <b>Название:</b> {template['name']}",
                f"📂 <b>Категория:</b> {template['category']}\n",
                "Примеры для разных дат:\n"
            ]

            for test_date in test_dates:
                # Format date in Russian
                date_str = f"{test_date.day:02d} {MONTHS_RU[test_date.month]['gen']}"

                # Calculate days until
                days_until = (test_date - datetime.now()).days
                date_before = (test_date - timedelta(days=1))
                date_before_str = f"{date_before.day:02d} {MONTHS_RU[date_before.month]['gen']}"

                # Prepare all variables
                test_vars = {
                    **sample_data,
                    'date': date_str,
                    'date_before': date_before_str,
                    'days_until': str(days_until)
                }

                # Replace variables in template
                test_msg = template['template']
                for var, value in test_vars.items():
                    test_msg = test_msg.replace(f"{{{var}}}", value)

                response.extend([
                    f"\n🗓 <b>Для даты {date_str}:</b>",
                    test_msg,
                    "➖➖➖➖➖➖➖➖➖➖"
                ])

            self.bot.reply_to(
                message,
                "\n".join(response),
                parse_mode='HTML'
            )

        except ValueError:
            self.bot.reply_to(
                message,
                "❌ **Неверный ID шаблона.</b>\n"
                "ID должен быть числом.",
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error testing template: {str(e)}")
            self.bot.reply_to(
                message,
                "❌ <b>Произошла ошибка при тестировании шаблона.</b>",
                parse_mode='HTML'
            )

    def game2048(self, message: telebot.types.Message):
        """Обработчик команды /game2048 - запуск игры 2048"""
        user_id = message.from_user.id
        
        # Проверяем, авторизован ли пользователь
        with self.db.get_connection() as conn:
            user_record = conn.execute(
                "SELECT telegram_id, is_subscribed FROM users WHERE telegram_id = ?",
                (user_id,)
            ).fetchone()
        
        # Если пользователь не авторизован, отправляем сообщение об ошибке
        if not user_record:
            self.bot.reply_to(
                message,
                "⛔ У вас нет доступа к этой функции. Пожалуйста, обратитесь к администратору для получения доступа.",
                parse_mode='HTML'
            )
            return
        
        # Создаем кнопку для запуска мини-приложения
        keyboard = telebot.types.InlineKeyboardMarkup()
        game_button = telebot.types.InlineKeyboardButton(
            text="Играть в 2048",
            url="https://t.me/PlayToTime_bot/Game2048"
        )
        keyboard.add(game_button)
        
        # Отправляем сообщение с кнопкой
        self.bot.send_message(
            message.chat.id,
            "🎮 <b>Игра 2048</b>\n\nНажмите на кнопку ниже, чтобы запустить игру:",
            parse_mode='HTML',
            reply_markup=keyboard
        )

    def birthdays_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для кнопки 'Дни рождения'"""
        # Создаем фиктивное сообщение для передачи в метод list_birthdays
        message = telebot.types.Message(
            message_id=call.message.message_id,
            from_user=call.from_user,
            date=call.message.date,
            chat=call.message.chat,
            content_type='text',
            options={},
            json_string=''
        )
        message.text = '/birthdays'
        
        # Отвечаем на callback, чтобы убрать индикатор загрузки
        self.bot.answer_callback_query(call.id)
        
        # Вызываем метод list_birthdays с созданным сообщением
        self.list_birthdays(message)
        
    def admin_users_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для группы команд 'Пользователи'"""
        # Проверяем, является ли пользователь администратором
        if call.from_user.id not in ADMIN_IDS:
            self.bot.answer_callback_query(call.id, "У вас нет прав администратора")
            return
            
        # Создаем клавиатуру с командами для управления пользователями
        keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
        
        # Кнопки команд
        add_user_button = telebot.types.InlineKeyboardButton(
            text="➕ Добавить пользователя",
            callback_data="cmd_add_user"
        )
        users_button = telebot.types.InlineKeyboardButton(
            text="📋 Справочник пользователей",
            callback_data="cmd_users"
        )
        remove_user_button = telebot.types.InlineKeyboardButton(
            text="➖ Удалить пользователя",
            callback_data="cmd_remove_user"
        )
        set_admin_button = telebot.types.InlineKeyboardButton(
            text="👑 Назначить администратора",
            callback_data="cmd_set_admin"
        )
        remove_admin_button = telebot.types.InlineKeyboardButton(
            text="👤 Отозвать права администратора",
            callback_data="cmd_remove_admin"
        )
        back_button = telebot.types.InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="back_to_main"
        )
        
        # Добавляем кнопки в клавиатуру
        keyboard.add(add_user_button, users_button)
        keyboard.add(remove_user_button)
        keyboard.add(set_admin_button, remove_admin_button)
        keyboard.add(back_button)
        
        # Отвечаем на callback
        self.bot.answer_callback_query(call.id)
        
        # Редактируем сообщение
        self.bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="👥 <b>Управление пользователями</b>\n\nВыберите команду:",
            parse_mode='HTML',
            reply_markup=keyboard
        )
        
    def admin_templates_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для группы команд 'Шаблоны'"""
        # Проверяем, является ли пользователь администратором
        if call.from_user.id not in ADMIN_IDS:
            self.bot.answer_callback_query(call.id, "У вас нет прав администратора")
            return
            
        # Создаем клавиатуру с командами для управления шаблонами
        keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
        
        # Кнопки команд
        get_templates_button = telebot.types.InlineKeyboardButton(
            text="📋 Список шаблонов",
            callback_data="cmd_get_templates"
        )
        set_template_button = telebot.types.InlineKeyboardButton(
            text="➕ Добавить шаблон",
            callback_data="cmd_set_template"
        )
        update_template_button = telebot.types.InlineKeyboardButton(
            text="✏️ Обновить шаблон",
            callback_data="cmd_update_template"
        )
        test_template_button = telebot.types.InlineKeyboardButton(
            text="🧪 Тест шаблона",
            callback_data="cmd_test_template"
        )
        preview_template_button = telebot.types.InlineKeyboardButton(
            text="👁️ Предпросмотр шаблона",
            callback_data="cmd_preview_template"
        )
        delete_template_button = telebot.types.InlineKeyboardButton(
            text="🗑️ Удалить шаблон",
            callback_data="cmd_delete_template"
        )
        activate_template_button = telebot.types.InlineKeyboardButton(
            text="✅ Активировать шаблон",
            callback_data="cmd_activate_template"
        )
        deactivate_template_button = telebot.types.InlineKeyboardButton(
            text="❌ Деактивировать шаблон",
            callback_data="cmd_deactivate_template"
        )
        help_template_button = telebot.types.InlineKeyboardButton(
            text="❓ Помощь по шаблонам",
            callback_data="cmd_help_template"
        )
        back_button = telebot.types.InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="back_to_main"
        )
        
        # Добавляем кнопки в клавиатуру
        keyboard.add(get_templates_button, set_template_button)
        keyboard.add(update_template_button, test_template_button)
        keyboard.add(preview_template_button, delete_template_button)
        keyboard.add(activate_template_button, deactivate_template_button)
        keyboard.add(help_template_button)
        keyboard.add(back_button)
        
        # Отвечаем на callback
        self.bot.answer_callback_query(call.id)
        
        # Редактируем сообщение
        self.bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="📋 <b>Управление шаблонами</b>\n\nВыберите команду:",
            parse_mode='HTML',
            reply_markup=keyboard
        )
        
    def admin_notifications_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для группы команд 'Рассылки'"""
        # Проверяем, является ли пользователь администратором
        if call.from_user.id not in ADMIN_IDS:
            self.bot.answer_callback_query(call.id, "У вас нет прав администратора")
            return
            
        # Создаем клавиатуру с командами для управления рассылками
        keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
        
        # Кнопки команд
        get_settings_button = telebot.types.InlineKeyboardButton(
            text="⚙️ Настройки уведомлений",
            callback_data="cmd_get_settings"
        )
        toggle_notifications_button = telebot.types.InlineKeyboardButton(
            text="🔔 Управление уведомлениями",
            callback_data="cmd_toggle_notifications"
        )
        set_setting_button = telebot.types.InlineKeyboardButton(
            text="➕ Добавить настройку",
            callback_data="cmd_set_setting"
        )
        edit_setting_button = telebot.types.InlineKeyboardButton(
            text="✏️ Изменить настройку",
            callback_data="cmd_edit_setting"
        )
        delete_setting_button = telebot.types.InlineKeyboardButton(
            text="🗑️ Удалить настройку",
            callback_data="cmd_delete_setting"
        )
        force_notify_button = telebot.types.InlineKeyboardButton(
            text="📢 Отправить уведомление",
            callback_data="cmd_force_notify"
        )
        back_button = telebot.types.InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="back_to_main"
        )
        
        # Добавляем кнопки в клавиатуру
        keyboard.add(get_settings_button, toggle_notifications_button)
        keyboard.add(set_setting_button, edit_setting_button)
        keyboard.add(delete_setting_button, force_notify_button)
        keyboard.add(back_button)
        
        # Отвечаем на callback
        self.bot.answer_callback_query(call.id)
        
        # Редактируем сообщение
        self.bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="📢 <b>Управление рассылками</b>\n\nВыберите команду:",
            parse_mode='HTML',
            reply_markup=keyboard
        )
        
    def admin_backup_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для группы команд 'Резервные копии'"""
        # Проверяем, является ли пользователь администратором
        if call.from_user.id not in ADMIN_IDS:
            self.bot.answer_callback_query(call.id, "У вас нет прав администратора")
            return
            
        # Создаем клавиатуру с командами для управления резервными копиями
        keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
        
        # Кнопки команд
        backup_button = telebot.types.InlineKeyboardButton(
            text="💾 Создать резервную копию",
            callback_data="cmd_backup"
        )
        list_backups_button = telebot.types.InlineKeyboardButton(
            text="📋 Список резервных копий",
            callback_data="cmd_list_backups"
        )
        restore_button = telebot.types.InlineKeyboardButton(
            text="🔄 Восстановить из копии",
            callback_data="cmd_restore"
        )
        back_button = telebot.types.InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="back_to_main"
        )
        
        # Добавляем кнопки в клавиатуру
        keyboard.add(backup_button, list_backups_button)
        keyboard.add(restore_button)
        keyboard.add(back_button)
        
        # Отвечаем на callback
        self.bot.answer_callback_query(call.id)
        
        # Редактируем сообщение
        self.bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="💾 <b>Управление резервными копиями</b>\n\nВыберите команду:",
            parse_mode='HTML',
            reply_markup=keyboard
        )
        
    def back_to_main_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для кнопки 'Назад'"""
        # Создаем фиктивное сообщение для передачи в метод start
        message = telebot.types.Message(
            message_id=call.message.message_id,
            from_user=call.from_user,
            date=call.message.date,
            chat=call.message.chat,
            content_type='text',
            options={},
            json_string=''
        )
        message.text = '/start'
        
        # Отвечаем на callback
        self.bot.answer_callback_query(call.id)
        
        # Вызываем метод start с созданным сообщением
        self.start(message)
        
    # Обработчики callback-запросов для команд администратора
    def cmd_add_user_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для команды 'Добавить пользователя'"""
        self._execute_command_from_callback(call, 'add_user')
        
    def cmd_users_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для команды 'Справочник пользователей'"""
        self._execute_command_from_callback(call, 'get_users_directory')
        
    def cmd_remove_user_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для команды 'Удалить пользователя'"""
        self._execute_command_from_callback(call, 'remove_user')
        
    def cmd_set_admin_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для команды 'Назначить администратора'"""
        self._execute_command_from_callback(call, 'set_admin')
        
    def cmd_remove_admin_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для команды 'Отозвать права администратора'"""
        self._execute_command_from_callback(call, 'remove_admin')
        
    def cmd_get_templates_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для команды 'Список шаблонов'"""
        self._execute_command_from_callback(call, 'get_templates')
        
    def cmd_set_template_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для команды 'Добавить шаблон'"""
        self._execute_command_from_callback(call, 'set_template')
        
    def cmd_update_template_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для команды 'Обновить шаблон'"""
        self._execute_command_from_callback(call, 'update_template')
        
    def cmd_test_template_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для команды 'Тест шаблона'"""
        self._execute_command_from_callback(call, 'test_template')
        
    def cmd_preview_template_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для команды 'Предпросмотр шаблона'"""
        self._execute_command_from_callback(call, 'preview_template')
        
    def cmd_delete_template_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для команды 'Удалить шаблон'"""
        self._execute_command_from_callback(call, 'delete_template')
        
    def cmd_activate_template_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для команды 'Активировать шаблон'"""
        self._execute_command_from_callback(call, 'activate_template')
        
    def cmd_deactivate_template_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для команды 'Деактивировать шаблон'"""
        self._execute_command_from_callback(call, 'deactivate_template')
        
    def cmd_help_template_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для команды 'Помощь по шаблонам'"""
        self._execute_command_from_callback(call, 'help_template')
        
    def cmd_get_settings_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для команды 'Настройки уведомлений'"""
        self._execute_command_from_callback(call, 'get_settings')
        
    def cmd_toggle_notifications_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для команды 'Управление уведомлениями пользователя'"""
        self._execute_command_from_callback(call, 'toggle_notifications')
        
    def cmd_set_setting_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для команды 'Добавить настройку уведомлений'"""
        self._execute_command_from_callback(call, 'set_setting')
        
    def cmd_edit_setting_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для команды 'Изменить настройку уведомлений'"""
        self._execute_command_from_callback(call, 'edit_setting')
        
    def cmd_delete_setting_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для команды 'Удалить настройку уведомлений'"""
        self._execute_command_from_callback(call, 'delete_setting')
        
    def cmd_force_notify_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для команды 'Отправить уведомление'"""
        self._execute_command_from_callback(call, 'force_notify')
        
    def cmd_backup_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для команды 'Создать резервную копию'"""
        self._execute_command_from_callback(call, 'create_backup')
        
    def cmd_list_backups_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для команды 'Список резервных копий'"""
        self._execute_command_from_callback(call, 'list_backups')
        
    def cmd_restore_callback(self, call: telebot.types.CallbackQuery):
        """Обработчик callback-запроса для команды 'Восстановить из копии'"""
        self._execute_command_from_callback(call, 'restore_backup')
        
    def _execute_command_from_callback(self, call: telebot.types.CallbackQuery, command: str):
        """Вспомогательный метод для выполнения команды из callback-запроса"""
        # Проверяем, является ли пользователь администратором
        if call.from_user.id not in ADMIN_IDS:
            self.bot.answer_callback_query(call.id, "У вас нет прав администратора")
            return
            
        # Создаем фиктивное сообщение для передачи в обработчик команды
        message = telebot.types.Message(
            message_id=call.message.message_id,
            from_user=call.from_user,
            date=call.message.date,
            chat=call.message.chat,
            content_type='text',
            options={},
            json_string=''
        )
        message.text = f'/{command}'
        
        # Отвечаем на callback
        self.bot.answer_callback_query(call.id)
        
        # Получаем обработчик команды
        handler = getattr(self, command, None)
        
        # Если обработчик найден, вызываем его
        if handler:
            handler(message)
        else:
            self.bot.send_message(
                call.message.chat.id,
                f"❌ Команда /{command} не найдена",
                parse_mode='HTML'
            )

def validate_template_html(html_text):
    #простая проверка на наличие недопустимых тегов, можно расширить
    allowed_tags = ["b", "i", "u", "i", "s", "code", "pre", "tg-spoiler", "blockquote", "a"]
    for tag in re.findall(r'<\/?([a-z]+)', html_text):
        if tag not in allowed_tags:
            return False
    return True