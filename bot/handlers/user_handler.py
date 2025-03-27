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
from .decorators import admin_required, log_errors, command_args

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
        self.bot.register_message_handler(self.get_users_directory, commands=['users', 'users_directory'])
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
            # Проверяем, является ли пользователь администратором
            is_admin = self.is_admin(message.from_user.id)
            
            # Приветственное сообщение с инструкциями
            welcome_text = (
                f"{EMOJI['wave']} <b>Добро пожаловать!</b>\n\n"
                f"Этот бот помогает отслеживать дни рождения и отправлять уведомления.\n\n"
            )
            
            # Добавляем инструкции в зависимости от прав пользователя
            if is_admin:
                welcome_text += (
                    f"{EMOJI['admin']} <b>Вы администратор бота</b>\n\n"
                    f"У вас есть доступ ко всем функциям бота.\n"
                    f"Выберите нужный раздел в меню ниже:"
                )
            else:
                welcome_text += (
                    f"Выберите нужный раздел в меню ниже:"
                )
            
            # Отправляем приветственное сообщение с клавиатурой
            keyboard = self.keyboard_manager.create_main_menu(is_admin)
            self.send_message(message.chat.id, welcome_text, reply_markup=keyboard)
            
            logger.info(f"Пользователь {message.from_user.id} запустил бота")
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике команды start: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
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
                self.send_message(
                    message.chat.id, 
                    f"{EMOJI['error']} <b>Ошибка:</b> Неверный формат команды.\n\n"
                    f"Используйте: <code>/add_user @username [имя] [фамилия] [день рождения в формате ДД.ММ.ГГГГ]</code>\n\n"
                    f"Например: <code>/add_user @username Иван Иванов 01.01.1990</code>"
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
            
            # Если указана дата рождения, парсим её
            birthday = None
            if len(args) > 3:
                try:
                    birthday_str = args[3]
                    birthday = datetime.strptime(birthday_str, '%d.%m.%Y').strftime('%Y-%m-%d')
                except ValueError:
                    self.send_message(
                        message.chat.id,
                        f"{EMOJI['error']} <b>Ошибка:</b> Неверный формат даты рождения. Используйте формат ДД.ММ.ГГГГ."
                    )
                    return
            
            # Создаем пользователя
            user = User(
                username=username,
                name=name,
                last_name=last_name,
                birthday=birthday,
                is_admin=False,
                notifications_enabled=True
            )
            
            # Добавляем пользователя в базу
            result = self.user_service.create_user(user)
            
            if result:
                # Формируем сообщение об успешном добавлении пользователя
                success_message = f"{EMOJI['success']} Пользователь @{username} успешно добавлен."
                
                if birthday:
                    birth_date = datetime.strptime(birthday, '%Y-%m-%d')
                    success_message += f"\nДень рождения: {birth_date.strftime('%d.%m.%Y')}"
                
                self.send_message(message.chat.id, success_message)
                logger.info(f"Добавлен пользователь @{username} администратором {message.from_user.id}")
            else:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Не удалось добавить пользователя."
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
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['info']} В справочнике нет пользователей."
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
            
            self.send_message(message.chat.id, users_text)
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
                self.send_message(
                    message.chat.id, 
                    f"{EMOJI['error']} <b>Ошибка:</b> Неверный формат команды.\n\n"
                    f"Используйте: <code>/remove_user @username</code>"
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
                self.send_message(
                    message.chat.id, 
                    f"{EMOJI['error']} <b>Ошибка:</b> Неверный формат команды.\n\n"
                    f"Используйте: <code>/set_admin @username</code>"
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
                self.send_message(
                    message.chat.id, 
                    f"{EMOJI['error']} <b>Ошибка:</b> Неверный формат команды.\n\n"
                    f"Используйте: <code>/remove_admin @username</code>"
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
                self.send_message(
                    message.chat.id, 
                    f"{EMOJI['error']} <b>Ошибка:</b> Неверный формат команды.\n\n"
                    f"Используйте: <code>/toggle_notifications @username</code>"
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
            is_admin = self.is_admin(call.from_user.id)
            
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
                f"Для добавления пользователя отправьте команду в формате:\n"
                f"<code>/add_user @username Имя Фамилия ДД.ММ.ГГГГ</code>\n\n"
                f"Например:\n"
                f"<code>/add_user @username Иван Иванов 01.01.1990</code>\n\n"
                f"После добавления пользователь будет доступен в справочнике и получать уведомления."
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