"""
Обработчик команд для отправки уведомлений.

Этот модуль содержит обработчик для отправки уведомлений всем пользователям
или выборочно выбранным пользователям.
"""

import logging
from typing import List, Dict, Set, Optional
from telebot import types

from .base_handler import BaseHandler
from ..core.models import User, NotificationTemplate
from ..services.notification_service import NotificationService
from ..services.user_service import UserService
from ..services.template_service import TemplateService
from .decorators import admin_required, log_errors
from ..utils.keyboard_manager import KeyboardManager
from ..constants import EMOJI

logger = logging.getLogger(__name__)


class NotificationHandler(BaseHandler):
    """
    Обработчик команд для отправки уведомлений.
    """
    
    def __init__(self, bot, notification_service: NotificationService, 
                 user_service: UserService, template_service: TemplateService):
        """
        Инициализация обработчика уведомлений.
        
        Args:
            bot: Экземпляр бота Telegram
            notification_service: Сервис для отправки уведомлений
            user_service: Сервис для работы с пользователями
            template_service: Сервис для работы с шаблонами
        """
        super().__init__(bot)
        self.notification_service = notification_service
        self.user_service = user_service
        self.template_service = template_service
        self.keyboard_manager = KeyboardManager()
        self.selected_users: Dict[int, Set[int]] = {}  # chat_id -> set of user_ids
        self.user_data: Dict[int, Dict[int, Dict[str, any]]] = {}  # chat_id -> user_id -> data
        
        # Создаем шаблон для произвольных сообщений, если его нет
        self._ensure_custom_message_template()
    
    def _ensure_custom_message_template(self) -> None:
        """
        Создание шаблона для произвольных сообщений, если он не существует.
        """
        try:
            template = self.template_service.get_template_by_name_and_category(
                name="custom_message",
                category="custom"
            )
            
            if not template:
                template = NotificationTemplate(
                    name="custom_message",
                    template="{message}",
                    category="custom",
                    is_active=True
                )
                self.template_service.create_template(template)
                logger.info("Создан шаблон для произвольных сообщений")
                
        except Exception as e:
            logger.error(f"Ошибка при создании шаблона произвольных сообщений: {str(e)}")
    
    def register_handlers(self) -> None:
        """
        Регистрация обработчиков команд.
        """
        # Обработчик команды отправки всем
        self.bot.message_handler(commands=['send_notification'])(self.cmd_send_notification)
        # Обработчик команды выборочной отправки
        self.bot.message_handler(commands=['selective_notification'])(self.cmd_selective_notification)
        # Обработчик callback-запросов для выбора пользователей
        self.bot.callback_query_handler(func=lambda call: call.data.startswith('select_user:'))(self.process_user_selection)
        self.bot.callback_query_handler(func=lambda call: call.data == 'confirm_selection')(self.confirm_user_selection)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cancel_selection')(self.cancel_user_selection)
    
    @admin_required
    @log_errors
    def cmd_send_notification(self, message: types.Message) -> None:
        """
        Обработчик команды /send_notification для отправки всем пользователям.
        """
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Отмена",
                callback_data="cancel_selection"
            )
        )
        
        self.send_message(
            message.chat.id,
            f"{EMOJI['bell']} <b>Отправка уведомления всем пользователям</b>\n\n"
            "Пожалуйста, введите текст сообщения для рассылки:",
            reply_markup=keyboard
        )
        self.set_next_handler(message.chat.id, self.process_broadcast_message)
    
    def process_broadcast_message(self, message: types.Message) -> None:
        """
        Обработка текста сообщения для массовой рассылки.
        """
        text = message.text
        result = self.notification_service.send_notification_to_all(
            template_name="custom_message",
            context={"message": text}
        )
        
        self.send_message(
            message.chat.id,
            f"{EMOJI['success']} <b>Результат рассылки:</b>\n\n"
            f"✅ Успешно отправлено: {result['success']}\n"
            f"❌ Не доставлено: {result['failed']}"
        )
    
    @admin_required
    @log_errors
    def cmd_selective_notification(self, message: types.Message) -> None:
        """
        Обработчик команды /selective_notification для выборочной отправки.
        """
        # Получаем список активных пользователей
        users = self.user_service.get_all_users()
        active_users = [user for user in users if user.is_notifications_enabled]
        
        if not active_users:
            self.send_message(
                message.chat.id,
                f"{EMOJI['warning']} <b>Нет активных пользователей</b>\n"
                "Невозможно отправить уведомление, так как нет пользователей с включенными уведомлениями."
            )
            return
        
        # Создаем клавиатуру с пользователями
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        
        # Инициализируем словарь данных пользователей для текущего чата
        chat_id = message.chat.id
        if chat_id not in self.user_data:
            self.user_data[chat_id] = {}
            
        # Создаем кнопки для пользователей
        for user in active_users:
            user_id = user.telegram_id
            full_name = f"{user.first_name} {user.last_name}".strip()
            display_name = full_name if full_name else f"@{user.username}" if user.username else f"ID: {user_id}"
            
            # Сохраняем данные пользователя
            self.user_data[chat_id][user_id] = {
                "display_name": display_name,
                "selected": False
            }
            
            keyboard.add(
                types.InlineKeyboardButton(
                    text=f"☐ {display_name}",
                    callback_data=f"select_user:{user_id}"
                )
            )
        
        # Добавляем кнопки управления
        keyboard.add(
            types.InlineKeyboardButton(
                text=f"{EMOJI['success']} Подтвердить выбор",
                callback_data="confirm_selection"
            ),
            types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Отмена",
                callback_data="cancel_selection"
            )
        )
        
        # Инициализируем множество выбранных пользователей
        self.selected_users[message.chat.id] = set()
        
        self.send_message(
            message.chat.id,
            f"{EMOJI['bell']} <b>Выборочная рассылка</b>\n\n"
            "Выберите получателей сообщения:",
            reply_markup=keyboard
        )
    
    def process_user_selection(self, call: types.CallbackQuery) -> None:
        """
        Обработка выбора пользователей.
        """
        try:
            user_id = int(call.data.split(':')[1])
            chat_id = call.message.chat.id
            
            if chat_id not in self.selected_users:
                self.selected_users[chat_id] = set()
                
            if chat_id not in self.user_data:
                self.user_data[chat_id] = {}
            
            # Изменяем состояние выбора пользователя
            if user_id in self.selected_users[chat_id]:
                self.selected_users[chat_id].remove(user_id)
                self.user_data[chat_id][user_id]["selected"] = False
            else:
                self.selected_users[chat_id].add(user_id)
                self.user_data[chat_id][user_id]["selected"] = True
            
            # Создаем новую клавиатуру с обновленными состояниями кнопок
            new_keyboard = types.InlineKeyboardMarkup(row_width=1)
            
            # Добавляем кнопки всех пользователей
            for uid, user_info in self.user_data[chat_id].items():
                display_name = user_info["display_name"]
                is_selected = user_info["selected"]
                
                button_text = f"☑ {display_name}" if is_selected else f"☐ {display_name}"
                new_keyboard.add(
                    types.InlineKeyboardButton(
                        text=button_text,
                        callback_data=f"select_user:{uid}"
                    )
                )
            
            # Добавляем кнопки управления
            new_keyboard.add(
                types.InlineKeyboardButton(
                    text=f"{EMOJI['success']} Подтвердить выбор",
                    callback_data="confirm_selection"
                ),
                types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Отмена",
                    callback_data="cancel_selection"
                )
            )
            
            # Обновляем сообщение с новой клавиатурой
            self.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=new_keyboard
            )
            
            # Отвечаем на callback-запрос
            self.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Ошибка при обработке выбора пользователя: {str(e)}")
            self.answer_callback_query(call.id, "Произошла ошибка при выборе пользователя")
    
    def confirm_user_selection(self, call: types.CallbackQuery) -> None:
        """
        Обработка подтверждения выбора пользователей.
        """
        chat_id = call.message.chat.id
        selected_users = self.selected_users.get(chat_id, set())
        
        if not selected_users:
            self.send_message(
                chat_id,
                f"{EMOJI['warning']} <b>Не выбрано ни одного пользователя</b>\n"
                "Пожалуйста, выберите хотя бы одного получателя."
            )
            return
        
        # Запрашиваем текст сообщения
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Отмена",
                callback_data="cancel_selection"
            )
        )
        
        self.send_message(
            chat_id,
            f"{EMOJI['bell']} <b>Введите текст сообщения</b>\n\n"
            f"Выбрано получателей: {len(selected_users)}",
            reply_markup=keyboard
        )
        self.set_next_handler(chat_id, lambda msg: self.send_selective_message(msg, selected_users))
    
    def send_selective_message(self, message: types.Message, selected_users: Set[int]) -> None:
        """
        Отправка сообщения выбранным пользователям.
        """
        text = message.text
        results = {"success": 0, "failed": 0}
        
        for user_id in selected_users:
            if self.notification_service.send_notification(
                user_id=user_id,
                template_name="custom_message",
                context={"message": text}
            ):
                results["success"] += 1
            else:
                results["failed"] += 1
        
        self.send_message(
            message.chat.id,
            f"{EMOJI['success']} <b>Результат рассылки:</b>\n\n"
            f"✅ Успешно отправлено: {results['success']}\n"
            f"❌ Не доставлено: {results['failed']}"
        )
    
    def cancel_user_selection(self, call: types.CallbackQuery) -> None:
        """
        Обработка отмены выбора пользователей.
        """
        chat_id = call.message.chat.id
        if chat_id in self.selected_users:
            del self.selected_users[chat_id]
        
        if chat_id in self.user_data:
            del self.user_data[chat_id]
        
        self.send_message(
            chat_id,
            f"{EMOJI['info']} <b>Операция отменена</b>"
        ) 