"""
Обработчики команд для игр и развлечений.

Этот модуль содержит обработчики для команд бота,
связанных с играми и развлекательными функциями.
"""

import logging
import telebot
from telebot import types

from bot.constants import EMOJI
from bot.services.user_service import UserService
from .base_handler import BaseHandler
from .decorators import log_errors

logger = logging.getLogger(__name__)


class GameHandler(BaseHandler):
    """
    Обработчик команд для игр и развлечений.
    
    Обрабатывает команды, связанные с перенаправлением на игры 
    и другие развлекательные мини-приложения в Telegram.
    """
    
    def __init__(self, bot: telebot.TeleBot, user_service: UserService):
        """
        Инициализация обработчика игр.
        
        Args:
            bot: Экземпляр бота Telegram
            user_service: Сервис для работы с пользователями
        """
        super().__init__(bot)
        self.user_service = user_service
        
    def register_handlers(self) -> None:
        """Регистрация обработчиков команд для игр и развлечений."""
        # Команды для игр и развлечений
        self.bot.message_handler(commands=['game2048'])(self.game_2048)
        self.bot.message_handler(commands=['writemate'])(self.writemate)
    
    @log_errors
    def game_2048(self, message: types.Message) -> None:
        """
        Обработчик команды /game2048 - запуск игры 2048.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            user_id = message.from_user.id
            
            # Проверяем доступ (пользователь должен быть администратором или существовать в базе)
            user_exists = self.user_service.get_user_by_id(user_id) is not None
            
            if not self.is_admin(user_id) and not user_exists:
                self.send_message(
                    message.chat.id,
                    "⛔ У вас нет доступа к этой функции. Пожалуйста, обратитесь к администратору для получения доступа."
                )
                return
            
            # Создаем кнопку для запуска мини-приложения
            keyboard = types.InlineKeyboardMarkup()
            game_button = types.InlineKeyboardButton(
                text="Играть в 2048",
                url="https://t.me/PlayToTime_bot/Game2048"
            )
            keyboard.add(game_button)
            
            # Отправляем сообщение с кнопкой
            self.send_message(
                message.chat.id,
                f"{EMOJI['game']} <b>Игра 2048</b>\n\nНажмите на кнопку ниже, чтобы запустить игру:",
                reply_markup=keyboard
            )
            
            logger.info(f"Пользователь {user_id} запросил доступ к игре 2048")
            
        except Exception as e:
            logger.error(f"Ошибка при запуске игры 2048: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @log_errors
    def writemate(self, message: types.Message) -> None:
        """
        Обработчик команды /writemate - открывает AI помощник для написания текстов.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            user_id = message.from_user.id
            
            # URL к сервису
            url = "https://t.me/PlayToTime_bot/WriteMate"
            
            # Создаем клавиатуру с кнопкой для перехода
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(
                text="✍️ ПишиЛегко",
                url=url
            ))
            
            # Отправляем сообщение с описанием и кнопкой
            self.send_message(
                message.chat.id,
                "📝 <b>ПишиЛегко</b> - твой AI помощник для создания и улучшения текстовых сообщений.\n\n"
                "• Создавай новые тексты\n"
                "• Улучшай существующие сообщения\n"
                "• Выбирай подходящий тон и формат\n\n"
                "Нажми на кнопку ниже для перехода:",
                reply_markup=keyboard
            )
            
            logger.info(f"Пользователь {user_id} запросил доступ к сервису ПишиЛегко")
            
        except Exception as e:
            logger.error(f"Ошибка при запуске сервиса ПишиЛегко: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            ) 