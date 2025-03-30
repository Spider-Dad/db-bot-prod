"""
Обработчики команд для управления пользователями.

Этот модуль содержит обработчики для команд бота,
связанных с добавлением, редактированием и удалением пользователей.
"""

import logging
import telebot
from telebot import types
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import re

from bot.core.models import User
from bot.services.user_service import UserService
from bot.constants import EMOJI, ERROR_MESSAGES, MONTHS_RU
from .base_handler import BaseHandler
from .decorators import admin_required, log_errors, command_args, registered_user_required

logger = logging.getLogger(__name__)


class UserHandler(BaseHandler):
    """
    Обработчик команд для управления пользователями.
    
    Обрабатывает команды, связанные с добавлением, редактированием 
    и удалением пользователей, а также управлением их правами.
    """
    
    def __init__(self, bot: telebot.TeleBot, user_service: UserService):
        """
        Инициализация обработчика пользователей.
        
        Args:
            bot: Экземпляр бота Telegram
            user_service: Сервис для работы с пользователями
        """
        super().__init__(bot)
        self.user_service = user_service
        
    def register_handlers(self) -> None:
        """
        Регистрация обработчиков для команд пользователя.
        """
        # Регистрация обработчиков команд для пользователя
        self.bot.register_message_handler(self.start, commands=['start'])
        self.bot.register_message_handler(self.list_birthdays, commands=['birthdays'])
        self.bot.register_message_handler(self.add_user, commands=['add_user'])
        self.bot.register_message_handler(self.remove_user, commands=['remove_user'])
        self.bot.register_message_handler(self.get_users_directory, commands=['users', 'users_directory', 'get_users_directory'])
        self.bot.register_message_handler(self.set_admin, commands=['set_admin'])
        self.bot.register_message_handler(self.remove_admin, commands=['remove_admin'])
        
        # Регистрация обработчиков callback-запросов для кнопок меню
        self.bot.callback_query_handler(func=lambda call: call.data == "menu_main")(self.menu_main_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == "menu_birthdays")(self.menu_birthdays_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == "menu_users")(self.menu_users_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == "menu_notifications")(self.menu_notifications_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == "menu_settings")(self.menu_settings_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == "menu_backup")(self.menu_backup_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == "menu_game")(self.menu_game_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == "menu_write")(self.menu_write_callback)
        
        # Регистрация обработчиков callback-запросов для команд управления пользователями
        self.bot.callback_query_handler(func=lambda call: call.data == "cmd_add_user")(self.cmd_add_user_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == "cmd_remove_user")(self.cmd_remove_user_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == "cmd_users_directory")(self.cmd_users_directory_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == "cmd_set_admin")(self.cmd_set_admin_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == "cmd_remove_admin")(self.cmd_remove_admin_callback)
    
    def start(self, message: types.Message) -> None:
        """
        Обработчик команды /start.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            # Получаем информацию о пользователе
            telegram_id = message.from_user.id
            username = message.from_user.username
            first_name = message.from_user.first_name
            last_name = message.from_user.last_name
            
            # Проверяем, есть ли у пользователя username
            if not username:
                # Сообщаем о необходимости установить username в Telegram
                no_username_text = (
                    f"{EMOJI['warning']} <b>Для регистрации в боте необходимо установить имя пользователя (@username) в Telegram</b>\n\n"
                    f"Для этого:\n"
                    f"1. Откройте настройки Telegram\n"
                    f"2. В разделе 'Аккаунт' нажмите на поле 'Имя пользователя' и установите его\n"
                    f"3. После установки имени пользователя вернитесь в бот и снова нажмите /start"
                )
                self.send_message(message.chat.id, no_username_text)
                logger.info(f"Пользователь {telegram_id} не имеет username, отправлена инструкция")
                return
            
            # Проверяем, существует ли пользователь в базе данных
            existing_user = self.user_service.get_user_by_telegram_id(telegram_id)
            
            # Если пользователь администратор, сразу показываем основное меню
            if self.is_admin(telegram_id):
                welcome_text = (
                    f"{EMOJI['wave']} <b>Добро пожаловать!</b>\n\n"
                    f"Этот бот помогает отслеживать дни рождения и отправлять уведомления.\n\n"
                    f"{EMOJI['admin']} <b>Вы администратор бота</b>\n\n"
                    f"У вас есть доступ ко всем функциям бота.\n"
                    f"Выберите нужный раздел в меню ниже:"
                )
                keyboard = self.keyboard_manager.create_main_menu(is_admin=True)
                self.send_message(message.chat.id, welcome_text, reply_markup=keyboard)
                logger.info(f"Администратор {telegram_id} запустил бота")
                return
            
            # Если пользователь уже существует в базе, показываем основное меню
            if existing_user:
                welcome_text = (
                    f"{EMOJI['wave']} <b>Добро пожаловать!</b>\n\n"
                    f"Этот бот помогает отслеживать дни рождения и отправлять уведомления.\n\n"
                    f"Выберите нужный раздел в меню ниже:"
                )
                keyboard = self.keyboard_manager.create_main_menu(is_admin=False)
                self.send_message(message.chat.id, welcome_text, reply_markup=keyboard)
                logger.info(f"Пользователь {telegram_id} запустил бота")
                return
            
            # Если пользователь не существует, отправляем запрос на регистрацию администраторам
            self.send_registration_request_to_admins(message.from_user)
            
            # Сообщаем пользователю о запросе на регистрацию
            waiting_text = (
                f"{EMOJI['hourglass']} <b>Запрос на регистрацию отправлен</b>\n\n"
                f"Ваша заявка на регистрацию принята! Пожалуйста, подождите некоторое время, пока "
                f"администратор добавит вас в систему. Вы получите уведомление, когда регистрация будет завершена."
            )
            self.send_message(message.chat.id, waiting_text)
            logger.info(f"Новый пользователь {telegram_id} с username @{username} запросил регистрацию")
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике команды start: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    def send_registration_request_to_admins(self, user: types.User) -> None:
        """
        Отправляет запрос на регистрацию всем администраторам.
        
        Args:
            user: Пользователь Telegram, запрашивающий регистрацию
        """
        try:
            # Получаем список Telegram ID всех администраторов
            admin_telegram_ids = self.user_service.get_admin_telegram_ids()
            
            # Если в базе нет администраторов, используем список из конфигурации
            if not admin_telegram_ids:
                admin_telegram_ids = ADMIN_IDS
            
            # Формируем сообщение для администраторов с готовой командой для добавления
            admin_message = (
                f"{EMOJI['bell']} <b>Новый запрос на доступ!</b>\n\n"
                f"👤 Пользователь: {user.first_name or ''} {user.last_name or ''}\n"
                f"🔍 Username: @{user.username}\n"
                f"🆔 Telegram ID: {user.id}\n\n"
                f"Для добавления пользователя скопируйте и выполните следующую команду, предварительно заменив Имя Фамилия и ГГГГ-ММ-ДД (для даты рождения) на реальные данные пользователя:\n\n"
                f"<code>/add_user @{user.username} Имя Фамилия ГГГГ-ММ-ДД {user.id}</code>\n\n"
                f"<b>Telegram ID пользователя ({user.id}) уже добавлен в команду!</b>"
            )
            
            # Отправляем сообщение всем администраторам
            for admin_id in admin_telegram_ids:
                self.send_message(
                    admin_id,
                    admin_message
                )
            
            logger.info(f"Запрос на регистрацию от @{user.username} отправлен администраторам")
        
        except Exception as e:
            logger.error(f"Ошибка при отправке запроса на регистрацию администраторам: {str(e)}")
    
    def notify_user_added(self, telegram_id: int, username: str) -> None:
        """
        Уведомляет пользователя о успешной регистрации в боте.
        
        Args:
            telegram_id: Telegram ID пользователя
            username: Username пользователя
        """
        try:
            welcome_text = (
                f"{EMOJI['success']} <b>Доступ предоставлен!</b>\n\n"
                f"Ваша заявка на регистрацию успешно выполнена, и теперь вы можете "
                f"использовать бот. Выберите нужный раздел в меню ниже:"
            )
            
            # Отправляем сообщение пользователю с клавиатурой
            keyboard = self.keyboard_manager.create_main_menu(is_admin=False)
            self.send_message(telegram_id, welcome_text, reply_markup=keyboard)
            
            logger.info(f"Пользователь @{username} (ID: {telegram_id}) уведомлен о регистрации")
        
        except Exception as e:
            logger.error(f"Ошибка при уведомлении пользователя о регистрации: {str(e)}")
    
    @registered_user_required
    @log_errors
    def list_birthdays(self, message: types.Message) -> None:
        """
        Обработчик команды /birthdays.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            # Получаем всех пользователей с днями рождения
            birthdays_list = self.user_service.get_all_users_with_birthdays()
            
            if not birthdays_list:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['info']} В базе данных нет дней рождения."
                )
                return
            
            # Формируем сообщение со списком дней рождений, сгруппированным по месяцам
            birthdays_text = f"👥 <b>Управление пользователями...</b>\n\n📋 Список дней рождения:\n\n"
            
            current_month = None
            
            for birthday in birthdays_list:
                month_num = birthday.get('month')
                
                # Если начался новый месяц, добавляем его заголовок
                if month_num != current_month:
                    if current_month is not None:
                        birthdays_text += "\n"  # Добавляем перенос строки между месяцами
                    current_month = month_num
                    birthdays_text += f"📅 <b>{MONTHS_RU[month_num]['nom']}:</b>\n"
                
                # Форматируем имя пользователя
                first_name = birthday.get('first_name', '')
                last_name = birthday.get('last_name', '')
                name = f"{first_name} {last_name}".strip() if last_name else first_name
                
                # Форматируем дату рождения
                birth_date_obj = datetime.strptime(birthday.get('birth_date'), '%Y-%m-%d').date()
                date_str = f"{birth_date_obj.day:02d} {MONTHS_RU[month_num]['gen']}"
                
                # Добавляем строку с днем рождения
                birthdays_text += f"👤 {name} - {date_str}\n"
            
            self.send_message(message.chat.id, birthdays_text)
            logger.info(f"Отправлен полный список дней рождения пользователю {message.from_user.id}")
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка дней рождения: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    def add_user(self, message: types.Message) -> None:
        """
        Обработчик команды /add_user.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            args = self.extract_command_args(message.text)
            
            if not args:
                # Создаем клавиатуру с кнопкой "Назад"
                keyboard = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_users"
                )
                keyboard.add(back_btn)
                
                # Отправляем информационное сообщение
                self.send_message(
                    message.chat.id, 
                    f"{EMOJI['plus']} <b>Добавление пользователя</b>\n\n"
                    f"Если вы знаете Telegram ID пользователя, используйте команду:\n"
                    f"<code>/add_user @username Имя Фамилия ГГГГ-ММ-ДД Telegram_ID</code>\n\n"
                    f"Например:\n"
                    f"<code>/add_user @username Иван Иванов 2000-01-01 1234567890</code>\n\n"
                    f"Если Telegram ID неизвестен, попросите пользователя нажать кнопку /start в боте.\n"
                    f"После этого вы получите сообщение с готовой командой для добавления пользователя.",
                    reply_markup=keyboard
                )
                return
            
            # Извлекаем имя пользователя
            username = args[0]
            if username.startswith('@'):
                username = username[1:]  # Убираем символ @ из имени пользователя
            
            # Проверяем, существует ли уже пользователь с таким именем
            existing_user = self.user_service.get_user_by_username(username)
            if existing_user:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Пользователь с именем @{username} уже существует."
                )
                return
            
            # Разбираем остальные аргументы
            name = args[1] if len(args) > 1 else username
            last_name = args[2] if len(args) > 2 else ""
            
            # Получаем Telegram ID пользователя из аргументов команды
            # Ищем последний числовой аргумент длиной больше 7 символов (это скорее всего Telegram ID)
            telegram_id = None
            birthday = None
            
            # Проверяем, может ли последний аргумент быть Telegram ID
            if len(args) > 3:
                last_arg = args[-1]
                if last_arg.isdigit() and len(last_arg) > 7:
                    telegram_id = int(last_arg)
                    logger.info(f"Используем Telegram ID из последнего аргумента команды: {telegram_id}")
                    # Если последний аргумент - ID, значит предпоследний может быть датой
                    if len(args) > 4:
                        birthday_str = args[-2]
                        try:
                            # Пробуем парсить как дату
                            try:
                                birthday = datetime.strptime(birthday_str, '%d.%m.%Y').strftime('%Y-%m-%d')
                            except ValueError:
                                birthday = datetime.strptime(birthday_str, '%Y-%m-%d').strftime('%Y-%m-%d')
                        except ValueError:
                            # Если не получилось, это не дата
                            birthday = None
                else:
                    # Последний аргумент не ID, пробуем его как дату
                    try:
                        birthday_str = last_arg
                        try:
                            birthday = datetime.strptime(birthday_str, '%d.%m.%Y').strftime('%Y-%m-%d')
                        except ValueError:
                            birthday = datetime.strptime(birthday_str, '%Y-%m-%d').strftime('%Y-%m-%d')
                    except ValueError:
                        # Если не получилось и это не дата, сообщаем об ошибке
                        self.send_message(
                            message.chat.id,
                            f"{EMOJI['error']} <b>Ошибка:</b> Неверный формат даты рождения. Используйте формат ДД.ММ.ГГГГ или ГГГГ-ММ-ДД."
                        )
                        return
            
            # Если нам не передали Telegram ID, пытаемся получить его через API
            if not telegram_id:
                try:
                    # Это работает только если пользователь уже взаимодействовал с ботом
                    user_info = self.bot.get_chat(f"@{username}")
                    if user_info:
                        telegram_id = user_info.id
                        logger.info(f"Получен Telegram ID через API: {telegram_id}")
                except Exception as e:
                    telegram_id = None
                    logger.warning(f"Не удалось получить Telegram ID для @{username} через API: {str(e)}")
                
                # Если не смогли получить ID, сообщаем об этом
                if not telegram_id:
                    self.send_message(
                        message.chat.id,
                        f"{EMOJI['warning']} <b>Не удалось автоматически получить Telegram ID пользователя @{username}</b>\n\n"
                        f"Пожалуйста, попросите пользователя нажать кнопку /start в боте.\n"
                        f"После этого вы получите сообщение с готовой командой для добавления пользователя."
                    )
                    return
            
            # Создаем объект пользователя
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=name,
                last_name=last_name,
                birth_date=birthday,
                is_admin=False,
                is_subscribed=True,
                is_notifications_enabled=True,
            )
            
            # Добавляем пользователя в базу
            result = self.user_service.create_user(user)
            
            if result:
                # Формируем сообщение об успешном добавлении пользователя
                success_message = f"{EMOJI['success']} Пользователь @{username} успешно добавлен."
                
                if birthday:
                    success_message += f" Дата рождения: {birthday}."
                
                success_message += f" Отправляю ему уведомление."
                
                # Уведомляем пользователя о регистрации
                self.notify_user_added(telegram_id, username)
                
                self.send_message(message.chat.id, success_message)
                logger.info(f"Администратор {message.from_user.id} добавил пользователя @{username}")
            else:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Не удалось добавить пользователя @{username}."
                )
        
        except Exception as e:
            logger.error(f"Ошибка при добавлении пользователя: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    def get_users_directory(self, message: types.Message) -> None:
        """
        Обработчик команды /get_users_directory.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            # Получаем всех пользователей
            users = self.user_service.get_all_users()
            
            if not users:
                # Создаем клавиатуру с кнопкой "Назад"
                keyboard = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_users"
                )
                keyboard.add(back_btn)
                
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['info']} В справочнике нет пользователей.",
                    reply_markup=keyboard
                )
                return
            
            # Разделяем пользователей на администраторов и обычных пользователей
            admins = [user for user in users if user.is_admin]
            regular_users = [user for user in users if not user.is_admin]
            
            # Формируем сообщение со списком пользователей
            users_text = f"{EMOJI['directory']} <b>Справочник пользователей</b>\n\n"
            
            # Добавляем администраторов
            if admins:
                users_text += f"👑 <b>Администраторы:</b>\n\n"
                
                for admin in admins:
                    # Имя и фамилия
                    name = f"{admin.first_name} {admin.last_name}".strip() if admin.last_name else admin.first_name
                    
                    # Логин
                    username = f"@{admin.username}" if admin.username else ""
                    
                    # Полная дата рождения
                    birth_date = ""
                    if admin.birth_date:
                        try:
                            birth_date_obj = datetime.strptime(admin.birth_date, '%Y-%m-%d').date()
                            birth_date = f"{birth_date_obj.strftime('%d.%m.%Y')}"
                        except ValueError:
                            birth_date = f"{admin.birth_date}"
                    
                    # Формируем строку с информацией о пользователе
                    users_text += f"👤 <b>{name}</b>\n"
                    users_text += f"• {username}\n" if username else ""
                    users_text += f"• {birth_date}\n" if birth_date else ""
                    users_text += f"• Подписка: {'✅' if admin.is_subscribed else '❌'}\n"
                    users_text += f"• Рассылка: {'✅' if admin.is_notifications_enabled else '❌'}\n"
                    users_text += f"• Telegram ID: {admin.telegram_id}\n\n"
            
            # Добавляем обычных пользователей
            if regular_users:
                users_text += f"👥 <b>Пользователи:</b>\n\n"
                
                for user in regular_users:
                    # Имя и фамилия
                    name = f"{user.first_name} {user.last_name}".strip() if user.last_name else user.first_name
                    
                    # Логин
                    username = f"@{user.username}" if user.username else ""
                    
                    # Полная дата рождения
                    birth_date = ""
                    if user.birth_date:
                        try:
                            birth_date_obj = datetime.strptime(user.birth_date, '%Y-%m-%d').date()
                            birth_date = f"{birth_date_obj.strftime('%d.%m.%Y')}"
                        except ValueError:
                            birth_date = f"{user.birth_date}"
                    
                    # Формируем строку с информацией о пользователе
                    users_text += f"👤 <b>{name}</b>\n"
                    users_text += f"• {username}\n" if username else ""
                    users_text += f"• {birth_date}\n" if birth_date else ""
                    users_text += f"• Подписка: {'✅' if user.is_subscribed else '❌'}\n"
                    users_text += f"• Рассылка: {'✅' if user.is_notifications_enabled else '❌'}\n"
                    users_text += f"• Telegram ID: {user.telegram_id}\n\n"
            
            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_users"
            )
            keyboard.add(back_btn)
            
            self.send_message(message.chat.id, users_text, reply_markup=keyboard)
            logger.info(f"Отправлен справочник пользователей администратору {message.from_user.id}")
            
        except Exception as e:
            logger.error(f"Ошибка при получении справочника пользователей: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    def remove_user(self, message: types.Message) -> None:
        """
        Обработчик команды /remove_user.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            args = self.extract_command_args(message.text)
            
            if not args:
                # Создаем клавиатуру с кнопкой "Назад"
                keyboard = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_users"
                )
                keyboard.add(back_btn)
                
                # Отправляем информационное сообщение
                self.send_message(
                    message.chat.id, 
                    f"{EMOJI['minus']} <b>Удаление пользователя</b>\n\n"
                    f"Для удаления пользователя отправьте команду в формате:\n"
                    f"<code>/remove_user @username</code>\n\n"
                    f"После удаления пользователь не будет получать уведомления о днях рождения.",
                    reply_markup=keyboard
                )
                return
            
            # Извлекаем имя пользователя
            username = args[0]
            if username.startswith('@'):
                username = username[1:]  # Убираем символ @ из имени пользователя
            
            # Проверяем, существует ли пользователь
            user = self.user_service.get_user_by_username(username)
            if not user:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Пользователь с именем @{username} не найден."
                )
                return
            
            # Удаляем пользователя
            user_id = user.telegram_id
            result = self.user_service.delete_user(user_id)
            
            if result:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['success']} Пользователь @{username} успешно удален."
                )
                logger.info(f"Удален пользователь @{username} администратором {message.from_user.id}")
            else:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Не удалось удалить пользователя."
                )
                
        except Exception as e:
            logger.error(f"Ошибка при удалении пользователя: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    def set_admin(self, message: types.Message) -> None:
        """
        Обработчик команды /set_admin.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            args = self.extract_command_args(message.text)
            
            if not args:
                # Создаем клавиатуру с кнопкой "Назад"
                keyboard = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_users"
                )
                keyboard.add(back_btn)
                
                # Отправляем информационное сообщение
                self.send_message(
                    message.chat.id, 
                    f"{EMOJI['admin']} <b>Назначение администратора</b>\n\n"
                    f"Для назначения пользователя администратором отправьте команду в формате:\n"
                    f"<code>/set_admin @username</code>\n\n"
                    f"После назначения пользователь получит доступ ко всем административным функциям бота.",
                    reply_markup=keyboard
                )
                return
            
            # Извлекаем имя пользователя
            username = args[0]
            if username.startswith('@'):
                username = username[1:]  # Убираем символ @ из имени пользователя
            
            # Проверяем, существует ли пользователь
            user = self.user_service.get_user_by_username(username)
            if not user:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Пользователь с именем @{username} не найден."
                )
                return
            
            # Проверяем, уже является ли пользователь администратором
            if user.is_admin:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['info']} Пользователь @{username} уже является администратором."
                )
                return
            
            # Назначаем пользователя администратором
            user_id = user.telegram_id
            result = self.user_service.set_admin_status(user_id, True)
            
            if result:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['success']} Пользователь @{username} назначен администратором."
                )
                logger.info(f"Пользователь @{username} назначен администратором пользователем {message.from_user.id}")
            else:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Не удалось назначить пользователя администратором."
                )
                
        except Exception as e:
            logger.error(f"Ошибка при назначении администратора: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    def remove_admin(self, message: types.Message) -> None:
        """
        Обработчик команды /remove_admin.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            args = self.extract_command_args(message.text)
            
            if not args:
                # Создаем клавиатуру с кнопкой "Назад"
                keyboard = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_users"
                )
                keyboard.add(back_btn)
                
                # Отправляем информационное сообщение
                self.send_message(
                    message.chat.id, 
                    f"{EMOJI['user']} <b>Отзыв прав администратора</b>\n\n"
                    f"Для отзыва прав администратора у пользователя отправьте команду в формате:\n"
                    f"<code>/remove_admin @username</code>\n\n"
                    f"После отзыва прав пользователь потеряет доступ к административным функциям бота.",
                    reply_markup=keyboard
                )
                return
            
            # Извлекаем имя пользователя
            username = args[0]
            if username.startswith('@'):
                username = username[1:]  # Убираем символ @ из имени пользователя
            
            # Проверяем, существует ли пользователь
            user = self.user_service.get_user_by_username(username)
            if not user:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Пользователь с именем @{username} не найден."
                )
                return
            
            # Проверяем, является ли пользователь администратором
            if not user.is_admin:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['info']} Пользователь @{username} не является администратором."
                )
                return
            
            # Отзываем права администратора
            user_id = user.telegram_id
            result = self.user_service.set_admin_status(user_id, False)
            
            if result:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['success']} У пользователя @{username} отозваны права администратора."
                )
                logger.info(f"У пользователя @{username} отозваны права администратора пользователем {message.from_user.id}")
            else:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Не удалось отозвать права администратора."
                )
                
        except Exception as e:
            logger.error(f"Ошибка при отзыве прав администратора: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    def toggle_notifications(self, message: types.Message) -> None:
        """
        Обработчик команды /toggle_notifications.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            args = self.extract_command_args(message.text)
            
            if not args:
                # Создаем клавиатуру с кнопкой "Назад"
                keyboard = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_users"
                )
                keyboard.add(back_btn)
                
                # Отправляем информационное сообщение
                self.send_message(
                    message.chat.id, 
                    f"{EMOJI['bell']} <b>Управление уведомлениями</b>\n\n"
                    f"Для включения или отключения уведомлений пользователя отправьте команду в формате:\n"
                    f"<code>/toggle_notifications @username</code>\n\n"
                    f"После выполнения команды статус получения уведомлений для пользователя изменится на противоположный.",
                    reply_markup=keyboard
                )
                return
            
            # Извлекаем имя пользователя
            username = args[0]
            if username.startswith('@'):
                username = username[1:]  # Убираем символ @ из имени пользователя
            
            # Проверяем, существует ли пользователь
            user = self.user_service.get_user_by_username(username)
            if not user:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Пользователь с именем @{username} не найден."
                )
                return
            
            # Получаем текущий статус уведомлений
            user_id = user.telegram_id
            current_status = user.notifications_enabled
            
            # Инвертируем статус
            new_status = not current_status
            result = self.user_service.toggle_notifications(user_id, new_status)
            
            if result:
                status_text = "включены" if new_status else "отключены"
                emoji = EMOJI['bell'] if new_status else EMOJI['bell_slash']
                
                self.send_message(
                    message.chat.id,
                    f"{emoji} Уведомления для пользователя @{username} {status_text}."
                )
                logger.info(f"Уведомления для пользователя @{username} {status_text} администратором {message.from_user.id}")
            else:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Не удалось изменить статус уведомлений."
                )
                
        except Exception as e:
            logger.error(f"Ошибка при изменении статуса уведомлений: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    # Обработчики callback-запросов для меню
    
    def menu_main_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик для возврата в главное меню.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем регистрацию пользователя
            user_id = call.from_user.id
            if not self.is_registered_user(user_id) and not self.is_admin(user_id):
                self.answer_callback_query(
                    call.id, 
                    "Вы не зарегистрированы в системе. Ожидайте подтверждения администратора.", 
                    show_alert=True
                )
                return
            
            is_admin = self.is_admin(user_id)
            
            # Текст для главного меню
            menu_text = (
                f"📋 <b>Главное меню</b>\n\n"
                f"Выберите нужный раздел:"
            )
            
            # Обновляем сообщение с клавиатурой
            keyboard = self.keyboard_manager.create_main_menu(is_admin)
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=menu_text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            # Отвечаем на callback-запрос
            self.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике callback-запроса menu_main: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    def menu_birthdays_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик для отображения списка дней рождения.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем регистрацию пользователя
            user_id = call.from_user.id
            if not self.is_registered_user(user_id) and not self.is_admin(user_id):
                self.answer_callback_query(
                    call.id, 
                    "Вы не зарегистрированы в системе. Ожидайте подтверждения администратора.", 
                    show_alert=True
                )
                return
            
            # Получаем всех пользователей с днями рождения
            birthdays_list = self.user_service.get_all_users_with_birthdays()
            
            if not birthdays_list:
                text = f"{EMOJI['info']} В базе данных нет дней рождения."
            else:
                # Формируем сообщение со списком дней рождений, сгруппированным по месяцам
                text = f"👥 <b>Управление пользователями...</b>\n\n📋 Список дней рождения:\n\n"
                
                current_month = None
                
                for birthday in birthdays_list:
                    month_num = birthday.get('month')
                    
                    # Если начался новый месяц, добавляем его заголовок
                    if month_num != current_month:
                        if current_month is not None:
                            text += "\n"  # Добавляем перенос строки между месяцами
                        current_month = month_num
                        text += f"📅 <b>{MONTHS_RU[month_num]['nom']}:</b>\n"
                    
                    # Форматируем имя пользователя
                    first_name = birthday.get('first_name', '')
                    last_name = birthday.get('last_name', '')
                    name = f"{first_name} {last_name}".strip() if last_name else first_name
                    
                    # Форматируем дату рождения
                    birth_date_obj = datetime.strptime(birthday.get('birth_date'), '%Y-%m-%d').date()
                    date_str = f"{birth_date_obj.day:02d} {MONTHS_RU[month_num]['gen']}"
                    
                    # Добавляем строку с днем рождения
                    text += f"👤 {name} - {date_str}\n"
            
            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_main"
            )
            keyboard.add(back_btn)
            
            # Обновляем сообщение
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            # Отвечаем на callback-запрос
            self.answer_callback_query(call.id)
            
            logger.info(f"Отправлен список дней рождения пользователю {call.from_user.id}")
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка дней рождения: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    def menu_users_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик для отображения меню управления пользователями.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем права администратора
            if not self.is_admin(call.from_user.id):
                self.answer_callback_query(call.id, "У вас нет прав администратора", show_alert=True)
                return
            
            # Текст для меню управления пользователями
            menu_text = (
                f"{EMOJI['users']} <b>Управление пользователями</b>\n\n"
                f"Выберите команду:"
            )
            
            # Обновляем сообщение с клавиатурой
            keyboard = self.keyboard_manager.create_users_menu()
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=menu_text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            # Отвечаем на callback-запрос
            self.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике callback-запроса menu_users: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    def menu_notifications_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик для отображения меню управления рассылками.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем права администратора
            if not self.is_admin(call.from_user.id):
                self.answer_callback_query(call.id, "У вас нет прав администратора", show_alert=True)
                return
            
            # Текст для меню управления рассылками
            menu_text = (
                f"{EMOJI['bell']} <b>Управление рассылками</b>\n\n"
                f"Выберите команду:"
            )
            
            # Обновляем сообщение с клавиатурой
            keyboard = self.keyboard_manager.create_notifications_menu()
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=menu_text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            # Отвечаем на callback-запрос
            self.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике callback-запроса menu_notifications: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    def menu_settings_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик для отображения меню настроек уведомлений.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем права администратора
            if not self.is_admin(call.from_user.id):
                self.answer_callback_query(call.id, "У вас нет прав администратора", show_alert=True)
                return
            
            # Текст для меню настроек уведомлений
            menu_text = (
                f"{EMOJI['setting']} <b>Управление настройками уведомлений</b>\n\n"
                f"В этом разделе вы можете управлять настройками уведомлений:\n"
                f"• Просматривать список настроек\n"
                f"• Добавлять новые настройки\n"
                f"• Обновлять существующие настройки\n"
                f"• Удалять настройки\n"
                f"• Активировать/деактивировать настройки\n\n"
                f"Выберите действие:"
            )
            
            # Обновляем сообщение с клавиатурой
            keyboard = self.keyboard_manager.create_settings_menu()
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=menu_text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            # Отвечаем на callback-запрос
            self.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике callback-запроса menu_settings: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    def menu_backup_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик для отображения меню управления резервными копиями.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем права администратора
            if not self.is_admin(call.from_user.id):
                self.answer_callback_query(call.id, "У вас нет прав администратора", show_alert=True)
                return
            
            # Текст для меню управления резервными копиями
            menu_text = (
                f"{EMOJI['backup']} <b>Управление резервными копиями</b>\n\n"
                f"Выберите команду:"
            )
            
            # Обновляем сообщение с клавиатурой
            keyboard = self.keyboard_manager.create_backup_menu()
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=menu_text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            # Отвечаем на callback-запрос
            self.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике callback-запроса menu_backup: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    def menu_game_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик для запуска игры 2048.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # URL игры 2048 (из game_handler.py)
            game_url = "https://t.me/PlayToTime_bot/Game2048"
            
            # Текст сообщения
            text = (
                f"{EMOJI['game']} <b>Игра 2048</b>\n\n"
                f"Нажмите на кнопку ниже, чтобы запустить игру 2048."
            )
            
            # Создаем клавиатуру с кнопками для игры и возврата
            keyboard = types.InlineKeyboardMarkup()
            
            # Кнопка для запуска игры
            game_button = types.InlineKeyboardButton(
                text="Играть в 2048",
                url=game_url
            )
            
            # Кнопка возврата в главное меню
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_main"
            )
            
            keyboard.add(game_button)
            keyboard.add(back_btn)
            
            # Обновляем сообщение
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            # Отвечаем на callback-запрос
            self.answer_callback_query(call.id, "Переход к игре 2048")
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике callback-запроса menu_game: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    def menu_write_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик для запуска функции "ПишиЛегко".
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # URL сервиса ПишиЛегко (из game_handler.py)
            write_url = "https://t.me/PlayToTime_bot/WriteMate"
            
            # Текст сообщения
            text = (
                f"{EMOJI['pencil']} <b>ПишиЛегко</b>\n\n"
                f"📝 <b>ПишиЛегко</b> - твой AI помощник для создания и улучшения текстовых сообщений.\n\n"
                f"• Создавай новые тексты\n"
                f"• Улучшай существующие сообщения\n"
                f"• Выбирай подходящий тон и формат\n\n"
                f"Нажмите на кнопку ниже для перехода:"
            )
            
            # Создаем клавиатуру с кнопками
            keyboard = types.InlineKeyboardMarkup()
            
            # Кнопка для перехода к сервису
            write_button = types.InlineKeyboardButton(
                text="✍️ ПишиЛегко",
                url=write_url
            )
            
            # Кнопка возврата в главное меню
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_main"
            )
            
            keyboard.add(write_button)
            keyboard.add(back_btn)
            
            # Обновляем сообщение
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            # Отвечаем на callback-запрос
            self.answer_callback_query(call.id, "Переход к сервису ПишиЛегко")
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике callback-запроса menu_write: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    # Обработчики callback-запросов для команд управления пользователями
    
    def cmd_add_user_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик для команды добавления пользователя.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем права администратора
            if not self.is_admin(call.from_user.id):
                self.answer_callback_query(call.id, "У вас нет прав администратора", show_alert=True)
                return
            
            # Текст с инструкцией по добавлению пользователя
            text = (
                f"{EMOJI['plus']} <b>Добавление пользователя</b>\n\n"
                f"Если вы знаете Telegram ID пользователя, используйте команду:\n"
                f"<code>/add_user @username Имя Фамилия ГГГГ-ММ-ДД Telegram_ID</code>\n\n"
                f"Например:\n"
                f"<code>/add_user @username Иван Иванов 2000-01-01 1234567890</code>\n\n"
                f"Если Telegram ID неизвестен, попросите пользователя нажать кнопку /start в боте.\n"
                f"После этого вы получите сообщение с готовой командой для добавления пользователя."
            )
            
            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_users"
            )
            keyboard.add(back_btn)
            
            # Обновляем сообщение
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            # Отвечаем на callback-запрос
            self.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике callback-запроса cmd_add_user: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    def cmd_remove_user_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик для команды удаления пользователя.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем права администратора
            if not self.is_admin(call.from_user.id):
                self.answer_callback_query(call.id, "У вас нет прав администратора", show_alert=True)
                return
            
            # Текст с инструкцией по удалению пользователя
            text = (
                f"{EMOJI['minus']} <b>Удаление пользователя</b>\n\n"
                f"Для удаления пользователя отправьте команду в формате:\n"
                f"<code>/remove_user @username</code>\n\n"
                f"После удаления пользователь не будет получать уведомления о днях рождения."
            )
            
            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_users"
            )
            keyboard.add(back_btn)
            
            # Обновляем сообщение
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            # Отвечаем на callback-запрос
            self.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике callback-запроса cmd_remove_user: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    def cmd_users_directory_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик для команды просмотра справочника пользователей.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем права администратора
            if not self.is_admin(call.from_user.id):
                self.answer_callback_query(call.id, "У вас нет прав администратора", show_alert=True)
                return
            
            # Получаем список всех пользователей
            users = self.user_service.get_all_users()
            
            if not users:
                text = f"{EMOJI['info']} Справочник пользователей пуст."
            else:
                # Разделяем пользователей на администраторов и обычных пользователей
                admins = [user for user in users if user.is_admin]
                regular_users = [user for user in users if not user.is_admin]
                
                # Формируем сообщение со списком пользователей
                text = f"{EMOJI['directory']} <b>Справочник пользователей</b>\n\n"
                
                # Добавляем администраторов
                if admins:
                    text += f"👑 <b>Администраторы:</b>\n\n"
                    
                    for admin in admins:
                        # Имя и фамилия
                        name = f"{admin.first_name} {admin.last_name}".strip() if admin.last_name else admin.first_name
                        
                        # Логин
                        username = f"@{admin.username}" if admin.username else ""
                        
                        # Полная дата рождения
                        birth_date = ""
                        if admin.birth_date:
                            try:
                                birth_date_obj = datetime.strptime(admin.birth_date, '%Y-%m-%d').date()
                                birth_date = f"{birth_date_obj.strftime('%d.%m.%Y')}"
                            except ValueError:
                                birth_date = f"{admin.birth_date}"
                        
                        # Формируем строку с информацией о пользователе
                        text += f"👤 <b>{name}</b>\n"
                        text += f"• {username}\n" if username else ""
                        text += f"• {birth_date}\n" if birth_date else ""
                        text += f"• Подписка: {'✅' if admin.is_subscribed else '❌'}\n"
                        text += f"• Рассылка: {'✅' if admin.is_notifications_enabled else '❌'}\n"
                        text += f"• Telegram ID: {admin.telegram_id}\n\n"
                
                # Добавляем обычных пользователей
                if regular_users:
                    text += f"👥 <b>Пользователи:</b>\n\n"
                    
                    for user in regular_users:
                        # Имя и фамилия
                        name = f"{user.first_name} {user.last_name}".strip() if user.last_name else user.first_name
                        
                        # Логин
                        username = f"@{user.username}" if user.username else ""
                        
                        # Полная дата рождения
                        birth_date = ""
                        if user.birth_date:
                            try:
                                birth_date_obj = datetime.strptime(user.birth_date, '%Y-%m-%d').date()
                                birth_date = f"{birth_date_obj.strftime('%d.%m.%Y')}"
                            except ValueError:
                                birth_date = f"{user.birth_date}"
                        
                        # Формируем строку с информацией о пользователе
                        text += f"👤 <b>{name}</b>\n"
                        text += f"• {username}\n" if username else ""
                        text += f"• {birth_date}\n" if birth_date else ""
                        text += f"• Подписка: {'✅' if user.is_subscribed else '❌'}\n"
                        text += f"• Рассылка: {'✅' if user.is_notifications_enabled else '❌'}\n"
                        text += f"• Telegram ID: {user.telegram_id}\n\n"
            
            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_users"
            )
            keyboard.add(back_btn)
            
            # Обновляем сообщение
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            # Отвечаем на callback-запрос
            self.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике callback-запроса cmd_users_directory: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    def cmd_set_admin_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик для команды назначения администратора.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем права администратора
            if not self.is_admin(call.from_user.id):
                self.answer_callback_query(call.id, "У вас нет прав администратора", show_alert=True)
                return
            
            # Текст с инструкцией по назначению администратора
            text = (
                f"{EMOJI['admin']} <b>Назначение администратора</b>\n\n"
                f"Для назначения пользователя администратором отправьте команду в формате:\n"
                f"<code>/set_admin @username</code>\n\n"
                f"После назначения пользователь получит доступ ко всем административным функциям бота."
            )
            
            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_users"
            )
            keyboard.add(back_btn)
            
            # Обновляем сообщение
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            # Отвечаем на callback-запрос
            self.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике callback-запроса cmd_set_admin: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    def cmd_remove_admin_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик для команды отзыва прав администратора.
        
        Args:
            call: Callback-запрос от кнопки
        """
        try:
            # Проверяем права администратора
            if not self.is_admin(call.from_user.id):
                self.answer_callback_query(call.id, "У вас нет прав администратора", show_alert=True)
                return
            
            # Текст с инструкцией по отзыву прав администратора
            text = (
                f"{EMOJI['user']} <b>Отзыв прав администратора</b>\n\n"
                f"Для отзыва прав администратора у пользователя отправьте команду в формате:\n"
                f"<code>/remove_admin @username</code>\n\n"
                f"После отзыва прав пользователь потеряет доступ к административным функциям бота."
            )
            
            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_users"
            )
            keyboard.add(back_btn)
            
            # Обновляем сообщение
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            # Отвечаем на callback-запрос
            self.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике callback-запроса cmd_remove_admin: {str(e)}")
            self.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)
    
    # ... остальные методы класса ... 