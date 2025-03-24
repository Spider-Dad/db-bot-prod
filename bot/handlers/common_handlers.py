"""
Обработчики общих команд бота.

Этот модуль содержит обработчики для общих команд бота,
таких как /start, /help и другие команды, доступные всем пользователям.
"""

import logging
import telebot
from telebot import types
from typing import Dict, List, Any, Optional

from bot.core.models import User
from bot.services.user_service import UserService
from bot.constants import EMOJI, TEMPLATE_HELP_TEXT
from .base_handler import BaseHandler

logger = logging.getLogger(__name__)


class CommonHandler(BaseHandler):
    """
    Обработчик общих команд бота.
    
    Обрабатывает команды, доступные всем пользователям бота.
    """
    
    def __init__(self, bot: telebot.TeleBot, user_service: UserService):
        """
        Инициализация обработчика общих команд.
        
        Args:
            bot: Экземпляр бота Telegram
            user_service: Сервис для работы с пользователями
        """
        super().__init__(bot)
        self.user_service = user_service
        
    def register_handlers(self) -> None:
        """Регистрация обработчиков общих команд."""
        
        self.bot.message_handler(commands=['start'])(self.handle_start)
        self.bot.message_handler(commands=['help'])(self.handle_help)
        self.bot.message_handler(commands=['help_template'])(self.handle_template_help)
        self.bot.message_handler(commands=['me'])(self.handle_me)
        
    def handle_start(self, message: types.Message) -> None:
        """
        Обработчик команды /start.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            user_id = message.from_user.id
            username = message.from_user.username
            first_name = message.from_user.first_name
            last_name = message.from_user.last_name
            
            # Проверяем, существует ли пользователь в базе
            user = self.user_service.get_user_by_telegram_id(user_id)
            
            if not user:
                # Создаем нового пользователя
                user = User(
                    telegram_id=user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                
                self.user_service.create_user(user)
                logger.info(f"Зарегистрирован новый пользователь: {username} ({user_id})")
                
                # Уведомляем администраторов о новом пользователе
                self._notify_admins_about_new_user(user)
            
            # Отправляем приветственное сообщение
            welcome_message = self._get_welcome_message(user)
            self.send_message(user_id, welcome_message)
            
        except Exception as e:
            logger.error(f"Ошибка обработки команды /start: {str(e)}")
            self.send_message(message.chat.id, "Произошла ошибка при обработке команды. Попробуйте позже.")
    
    def handle_help(self, message: types.Message) -> None:
        """
        Обработчик команды /help.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            user_id = message.from_user.id
            
            help_message = f"""<b>{EMOJI['info']} Помощь по командам бота</b>

<b>Основные команды:</b>
/start - Начать работу с ботом
/help - Показать эту справку
/me - Показать информацию о вашем профиле
/help_template - Справка по форматированию шаблонов

<b>Для администраторов:</b>
/users - Список всех пользователей
/add_user - Добавить нового пользователя
/remove_user - Удалить пользователя
/set_admin - Назначить администратора
/remove_admin - Отозвать права администратора

<b>Управление уведомлениями:</b>
/templates - Список всех шаблонов
/set_template - Добавить новый шаблон
/update_template - Обновить существующий шаблон
/delete_template - Удалить шаблон
/preview_template - Предпросмотр шаблона

<b>Настройки:</b>
/settings - Показать настройки уведомлений
/toggle_notifications - Включить/отключить уведомления
/backup - Создать резервную копию базы данных
/restore_backup - Восстановить из резервной копии"""

            self.send_message(user_id, help_message)
            
        except Exception as e:
            logger.error(f"Ошибка обработки команды /help: {str(e)}")
            self.send_message(message.chat.id, "Произошла ошибка при обработке команды. Попробуйте позже.")
    
    def handle_template_help(self, message: types.Message) -> None:
        """
        Обработчик команды /help_template.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            user_id = message.from_user.id
            
            # Отправляем справку по форматированию шаблонов
            self.send_message(user_id, TEMPLATE_HELP_TEXT)
            
        except Exception as e:
            logger.error(f"Ошибка обработки команды /help_template: {str(e)}")
            self.send_message(message.chat.id, "Произошла ошибка при обработке команды. Попробуйте позже.")
    
    def handle_me(self, message: types.Message) -> None:
        """
        Обработчик команды /me.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            user_id = message.from_user.id
            
            # Получаем пользователя из базы
            user = self.user_service.get_user_by_telegram_id(user_id)
            
            if not user:
                self.send_message(user_id, "Вы не зарегистрированы в системе. Используйте /start для регистрации.")
                return
            
            # Формируем сообщение с информацией о пользователе
            profile_message = f"""<b>{EMOJI['user']} Ваш профиль</b>

<b>ID:</b> {user.id}
<b>Telegram ID:</b> {user.telegram_id}
<b>Имя пользователя:</b> {f'@{user.username}' if user.username else 'Не указано'}
<b>Имя:</b> {user.first_name or 'Не указано'}
<b>Фамилия:</b> {user.last_name or 'Не указано'}
<b>Дата рождения:</b> {user.birth_date or 'Не указана'}
<b>Администратор:</b> {'Да' if user.is_admin else 'Нет'}
<b>Подписка на уведомления:</b> {'Включена' if user.is_notifications_enabled else 'Отключена'}
<b>Дата регистрации:</b> {user.created_at if isinstance(user.created_at, str) else user.created_at.strftime('%d.%m.%Y %H:%M:%S')}"""
            
            self.send_message(user_id, profile_message)
            
        except Exception as e:
            logger.error(f"Ошибка обработки команды /me: {str(e)}")
            self.send_message(message.chat.id, "Произошла ошибка при обработке команды. Попробуйте позже.")
    
    def _get_welcome_message(self, user: User) -> str:
        """
        Формирование приветственного сообщения.
        
        Args:
            user: Пользователь
            
        Returns:
            Текст приветственного сообщения
        """
        is_new_user = user.id is None
        
        if is_new_user:
            return f"""<b>👋 Добро пожаловать в BirthdayBot!</b>

Привет, {user.first_name or 'пользователь'}! Этот бот поможет вам не забыть о днях рождения ваших коллег и вовремя присоединиться к сбору на подарок.

Используйте /help для просмотра доступных команд.

📝 Обратите внимание, что для полноценной работы с ботом вам необходимо дождаться подтверждения от администратора."""
        else:
            return f"""<b>👋 С возвращением в BirthdayBot!</b>

Рад видеть вас снова, {user.first_name or 'пользователь'}!

Используйте /help для просмотра доступных команд или /me для просмотра информации о вашем профиле."""
    
    def _notify_admins_about_new_user(self, user: User) -> None:
        """
        Отправка уведомления администраторам о новом пользователе.
        
        Args:
            user: Новый пользователь
        """
        # Получаем список администраторов из базы данных
        admin_ids = self.user_service.get_admin_user_ids()
        
        # Формируем текст уведомления
        notification_text = f"""<b>{EMOJI['info']} Новый пользователь</b>

<b>Telegram ID:</b> {user.telegram_id}
<b>Имя пользователя:</b> {f'@{user.username}' if user.username else 'Не указано'}
<b>Имя:</b> {user.first_name or 'Не указано'}
<b>Фамилия:</b> {user.last_name or 'Не указано'}

Используйте <code>/add_user @{user.username or ''}</code> для добавления пользователя в базу с правом получать уведомления."""
        
        # Отправляем уведомление каждому администратору
        for admin_id in admin_ids:
            self.send_message(admin_id, notification_text) 