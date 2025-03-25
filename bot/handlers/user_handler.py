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
        """Регистрация обработчиков команд для управления пользователями."""
        # Базовые команды
        self.bot.message_handler(commands=['start'])(self.start)
        self.bot.message_handler(commands=['birthdays'])(self.list_birthdays)
        
        # Команды для работы с пользователями (только для администраторов)
        self.bot.message_handler(commands=['add_user'])(self.add_user)
        self.bot.message_handler(commands=['get_users_directory'])(self.get_users_directory)
        self.bot.message_handler(commands=['remove_user'])(self.remove_user)
        self.bot.message_handler(commands=['set_admin'])(self.set_admin)
        self.bot.message_handler(commands=['remove_admin'])(self.remove_admin)
        self.bot.message_handler(commands=['toggle_notifications'])(self.toggle_notifications)
        
        # Обработчики callback-запросов для команд
        self.bot.callback_query_handler(func=lambda call: call.data == 'birthdays')(self.birthdays_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_add_user')(self.cmd_add_user_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_users')(self.cmd_users_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_remove_user')(self.cmd_remove_user_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_set_admin')(self.cmd_set_admin_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_remove_admin')(self.cmd_remove_admin_callback)
    
    def start(self, message: types.Message) -> None:
        """
        Обработчик команды /start.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            # Приветственное сообщение с инструкциями
            welcome_text = (
                f"{EMOJI['wave']} <b>Добро пожаловать!</b>\n\n"
                f"Этот бот помогает отслеживать дни рождения и отправлять уведомления.\n\n"
            )
            
            # Добавляем инструкции в зависимости от прав пользователя
            if self.is_admin(message.from_user.id):
                welcome_text += (
                    f"{EMOJI['admin']} <b>Вы администратор бота</b>\n\n"
                    f"Вы можете:\n"
                    f"• Добавлять и удалять пользователей\n"
                    f"• Управлять шаблонами уведомлений\n"
                    f"• Настраивать расписание уведомлений\n\n"
                    f"Используйте команду /get_users_directory для просмотра справочника пользователей."
                )
            else:
                welcome_text += (
                    f"Используйте команду /birthdays для просмотра списка ближайших дней рождения."
                )
            
            # Отправляем приветственное сообщение
            self.send_message(message.chat.id, welcome_text)
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
            # Получаем пользователей с ближайшими днями рождения (30 дней)
            birthday_info = self.user_service.get_users_with_upcoming_birthdays(30)
            
            if not birthday_info:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['info']} В ближайшие 30 дней нет дней рождения."
                )
                return
            
            # Формируем сообщение со списком дней рождения
            birthdays_text = f"{EMOJI['gift']} <b>Ближайшие дни рождения:</b>\n\n"
            
            for info in birthday_info:
                user = info.get("user")
                days_until = info.get("days_until", 0)
                
                if not user:
                    continue
                    
                name = f"{user.first_name} {user.last_name}".strip() if user.last_name else user.first_name
                
                # Формируем строку с датой и именем
                if days_until == 0:
                    # День рождения сегодня
                    birthday_text = f"{EMOJI['party']} <b>СЕГОДНЯ!</b> {name}"
                elif days_until == 1:
                    # День рождения завтра
                    birthday_text = f"{EMOJI['clock']} <b>Завтра</b> - {name}"
                else:
                    # День рождения в ближайшие дни
                    if user.birth_date:
                        try:
                            birthday_date = datetime.strptime(user.birth_date, '%Y-%m-%d').date()
                            birthday_text = f"{EMOJI['calendar']} <b>{birthday_date.strftime('%d.%m')}</b> ({days_until} дн.) - {name}"
                        except ValueError:
                            birthday_text = f"{EMOJI['calendar']} <b>через {days_until} дн.</b> - {name}"
                    else:
                        birthday_text = f"{EMOJI['calendar']} <b>через {days_until} дн.</b> - {name}"
                
                birthdays_text += f"{birthday_text}\n"
            
            self.send_message(message.chat.id, birthdays_text)
            logger.info(f"Отправлен список дней рождения пользователю {message.from_user.id}")
            
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
            
            # Формируем сообщение со списком пользователей
            users_text = f"{EMOJI['user']} <b>Справочник пользователей ({len(users)}):</b>\n\n"
            
            for user in users:
                user_id = user.telegram_id
                username = user.username or "Нет имени пользователя"
                first_name = user.first_name or ""
                last_name = user.last_name or ""
                name = f"{first_name} {last_name}".strip() or "Имя не указано"
                birthday = user.birth_date
                is_admin = user.is_admin
                notifications_enabled = user.is_notifications_enabled
                
                # Форматируем дату рождения
                birthday_str = "Не указан"
                if birthday:
                    try:
                        birth_date = datetime.strptime(birthday, '%Y-%m-%d')
                        birthday_str = birth_date.strftime('%d.%m.%Y')
                    except ValueError:
                        birthday_str = birthday
                
                # Иконки для статусов
                admin_status = f"{EMOJI['admin']} Администратор" if is_admin else ""
                notify_status = EMOJI['active'] if notifications_enabled else EMOJI['inactive']
                
                # Формируем строку с информацией о пользователе
                user_text = (
                    f"<b>{name}</b> (@{username}) {admin_status}\n"
                    f"ID: {user_id}\n"
                    f"День рождения: {birthday_str}\n"
                    f"Уведомления: {notify_status}\n\n"
                )
                
                users_text += user_text
            
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
    
    # Обработчики callback-запросов
    
    @log_errors
    def birthdays_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды birthdays.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.list_birthdays(call.message)
    
    @log_errors
    def cmd_add_user_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды add_user.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.send_message(
            call.message.chat.id,
            f"{EMOJI['info']} Введите команду в формате: <code>/add_user @username [имя] [фамилия] [день рождения в формате ДД.ММ.ГГГГ]</code>\n\n"
            f"Например: <code>/add_user @username Иван Иванов 01.01.1990</code>"
        )
    
    @log_errors
    def cmd_users_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды get_users_directory.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.get_users_directory(call.message)
    
    @log_errors
    def cmd_remove_user_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды remove_user.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.send_message(
            call.message.chat.id,
            f"{EMOJI['info']} Введите команду в формате: <code>/remove_user @username</code>"
        )
    
    @log_errors
    def cmd_set_admin_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды set_admin.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.send_message(
            call.message.chat.id,
            f"{EMOJI['info']} Введите команду в формате: <code>/set_admin @username</code>"
        )
    
    @log_errors
    def cmd_remove_admin_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды remove_admin.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.send_message(
            call.message.chat.id,
            f"{EMOJI['info']} Введите команду в формате: <code>/remove_admin @username</code>"
        ) 