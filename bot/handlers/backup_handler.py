"""
Обработчики команд для управления резервными копиями базы данных.

Этот модуль содержит обработчики для команд бота,
связанных с созданием и восстановлением резервных копий базы данных.
"""

import logging
import os
import telebot
from telebot import types
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from bot.services.backup_service import BackupService
from bot.services.user_service import UserService
from bot.constants import EMOJI, ERROR_MESSAGES
from .base_handler import BaseHandler
from .decorators import admin_required, log_errors, command_args
from config import ADMIN_IDS

logger = logging.getLogger(__name__)


class BackupHandler(BaseHandler):
    """
    Обработчик команд для управления резервными копиями базы данных.
    
    Обрабатывает команды, связанные с созданием и восстановлением
    резервных копий базы данных.
    """
    
    def __init__(self, bot: telebot.TeleBot, backup_service: BackupService, user_service: UserService):
        """
        Инициализация обработчика резервного копирования.
        
        Args:
            bot: Экземпляр бота Telegram
            backup_service: Сервис для работы с резервными копиями
            user_service: Сервис для работы с пользователями
        """
        super().__init__(bot)
        self.backup_service = backup_service
        self.user_service = user_service
        
    def register_handlers(self) -> None:
        """Регистрация обработчиков команд для управления резервными копиями."""
        # Команды для работы с резервными копиями
        self.bot.message_handler(commands=['backup', 'create_backup'])(self.create_backup)
        self.bot.message_handler(commands=['get_backups', 'list_backups'])(self.get_backups)
        self.bot.message_handler(commands=['restore', 'restore_backup'])(self.restore_backup)
        self.bot.message_handler(commands=['delete_backup'])(self.delete_backup)
        self.bot.message_handler(commands=['help_backup'])(self.help_backup)
        
        # Обработчики документов (для загрузки резервных копий)
        self.bot.message_handler(content_types=['document'])(self.handle_document)
        
        # Обработчики callback-запросов
        self.bot.callback_query_handler(func=lambda call: call.data.startswith('restore_'))(self.confirm_restore)
        self.bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_restore'))(self.cancel_restore)
        self.bot.callback_query_handler(func=lambda call: call.data.startswith('delete_backup_'))(self.confirm_delete)
        self.bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_delete'))(self.cancel_delete)
        
        # Обработчики для команд в меню
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_create_backup')(self.cmd_backup_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_list_backups')(self.cmd_get_backups_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_restore_backup')(self.cmd_restore_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_delete_backup')(self.cmd_delete_backup_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_help_backup')(self.cmd_help_backup_callback)
    
    @admin_required
    @log_errors
    def create_backup(self, message: types.Message) -> None:
        """
        Обработчик команды /backup.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            # Отправляем сообщение о начале создания резервной копии
            self.send_message(
                message.chat.id,
                f"{EMOJI['loading']} Создание резервной копии базы данных..."
            )
            
            # Создаем резервную копию
            backup_path = self.backup_service.create_backup()
            
            if not backup_path or not os.path.exists(backup_path):
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Не удалось создать резервную копию."
                )
                return
            
            # Получаем имя файла резервной копии
            backup_filename = os.path.basename(backup_path)
            backup_size = os.path.getsize(backup_path) / 1024  # размер в KB
            
            # Формируем сообщение об успешном создании резервной копии
            success_message = (
                f"{EMOJI['success']} Резервная копия успешно создана:\n\n"
                f"<b>Имя файла:</b> {backup_filename}\n"
                f"<b>Размер:</b> {backup_size:.2f} KB\n"
                f"<b>Дата создания:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
            )
            
            self.send_message(message.chat.id, success_message)
            logger.info(f"Создана резервная копия базы данных администратором {message.from_user.id}: {backup_path}")
            
        except Exception as e:
            logger.error(f"Ошибка при создании резервной копии: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка при создании резервной копии:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    def get_backups(self, message: types.Message) -> None:
        """
        Обработчик команды /get_backups.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            # Получаем список резервных копий
            backups = self.backup_service.get_backup_list()
            
            if not backups:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['info']} Резервных копий не найдено."
                )
                return
            
            # Формируем сообщение со списком резервных копий
            backups_text = f"{EMOJI['backup']} <b>Список резервных копий ({len(backups)}):</b>\n\n"
            
            for backup in backups:
                backup_name = backup.get('filename')
                backup_date = backup.get('created_at').strftime('%d.%m.%Y %H:%M:%S') if backup.get('created_at') else 'Неизвестно'
                backup_size = backup.get('size', 0) / 1024  # размер в KB
                
                backup_text = (
                    f"<b>{backup_name}</b>\n"
                    f"Дата создания: {backup_date}\n"
                    f"Размер: {backup_size:.2f} KB\n\n"
                )
                
                backups_text += backup_text
            
            # Добавляем инструкции
            backups_text += (
                f"Для восстановления из резервной копии используйте:\n"
                f"<code>/restore [имя_файла]</code>\n\n"
                f"Для удаления резервной копии используйте:\n"
                f"<code>/delete_backup [имя_файла]</code>"
            )
            
            self.send_message(message.chat.id, backups_text)
            logger.info(f"Отправлен список резервных копий администратору {message.from_user.id}")
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка резервных копий: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка при получении списка резервных копий:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    def restore_backup(self, message: types.Message, args: List[str] = None) -> None:
        """
        Обработчик команды /restore.
        
        Args:
            message: Сообщение от пользователя
            args: Аргументы команды
        """
        try:
            # Отладка
            logger.info(f"restore_backup: исходный текст сообщения: '{message.text}'")
            logger.info(f"restore_backup: полученные аргументы: {args}")
            
            # Извлекаем аргументы из сообщения, если они не были переданы
            if args is None:
                args = self.extract_command_args(message.text)
                logger.info(f"restore_backup: аргументы после извлечения: {args}")
            
            # Проверяем наличие аргументов
            if not args or len(args) < 1:
                # Создаем клавиатуру с кнопкой "Назад"
                keyboard = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_backup"
                )
                keyboard.add(back_btn)
                
                # Если аргументы не переданы, отправляем информационное сообщение
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['info']} Введите команду в формате: <code>/restore [имя_файла]</code>\n\n"
                    f"Например: <code>/restore database_backup_2023-07-15.db</code>",
                    reply_markup=keyboard
                )
                return
                
            # Извлекаем имя файла резервной копии
            backup_filename = args[0]
            
            # Проверяем существование резервной копии
            backup_path = self.backup_service.get_backup_path(backup_filename)
            
            if not backup_path or not os.path.exists(backup_path):
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Резервная копия с именем '{backup_filename}' не найдена."
                )
                return
            
            # Запрашиваем подтверждение восстановления
            confirm_markup = types.InlineKeyboardMarkup()
            confirm_button = types.InlineKeyboardButton(
                "Да, восстановить",
                callback_data=f"restore_{backup_filename}"
            )
            cancel_button = types.InlineKeyboardButton("Отмена", callback_data="cancel_restore")
            confirm_markup.add(confirm_button)
            confirm_markup.add(cancel_button)
            
            self.send_message(
                message.chat.id,
                f"{EMOJI['warning']} <b>Внимание!</b> Вы собираетесь восстановить базу данных из резервной копии '{backup_filename}'.\n\n"
                f"Это приведет к замене текущих данных. Все изменения, сделанные после создания резервной копии, будут потеряны.\n\n"
                f"Вы уверены, что хотите продолжить?",
                reply_markup=confirm_markup
            )
            
        except Exception as e:
            logger.error(f"Ошибка при подготовке к восстановлению из резервной копии: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    def confirm_restore(self, call: types.CallbackQuery) -> None:
        """
        Обработчик подтверждения восстановления из резервной копии.
        
        Args:
            call: Callback-запрос
        """
        try:
            # Извлекаем имя файла резервной копии
            backup_filename = call.data.split('_', 1)[1]
            
            # Отвечаем на callback-запрос
            self.bot.answer_callback_query(call.id)
            
            # Изменяем сообщение
            self.bot.edit_message_text(
                f"{EMOJI['process']} Восстановление из резервной копии '{backup_filename}'...",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=None
            )
            
            # Восстанавливаем из резервной копии
            result = self.backup_service.restore_from_backup(backup_filename)
            
            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_backup"
            )
            keyboard.add(back_btn)
            
            if result:
                self.bot.edit_message_text(
                    f"{EMOJI['success']} База данных успешно восстановлена из резервной копии '{backup_filename}'.",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=keyboard
                )
                logger.info(f"Восстановлена база данных из резервной копии '{backup_filename}' администратором {call.from_user.id}")
            else:
                self.bot.edit_message_text(
                    f"{EMOJI['error']} <b>Ошибка:</b> Не удалось восстановить базу данных из резервной копии '{backup_filename}'.",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
                
        except Exception as e:
            logger.error(f"Ошибка при восстановлении из резервной копии: {str(e)}")
            
            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_backup"
            )
            keyboard.add(back_btn)
            
            self.send_message(
                call.message.chat.id,
                f"{EMOJI['error']} <b>Ошибка при восстановлении:</b> {str(e)}",
                reply_markup=keyboard
            )
    
    @admin_required
    @log_errors
    def cancel_restore(self, call: types.CallbackQuery) -> None:
        """
        Обработчик отмены восстановления из резервной копии.
        
        Args:
            call: Callback-запрос
        """
        # Отвечаем на callback-запрос
        self.bot.answer_callback_query(call.id)
        
        # Создаем клавиатуру с кнопкой "Назад"
        keyboard = types.InlineKeyboardMarkup()
        back_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['back']} Назад", 
            callback_data="menu_backup"
        )
        keyboard.add(back_btn)
        
        # Изменяем сообщение
        self.bot.edit_message_text(
            f"{EMOJI['info']} Восстановление из резервной копии отменено.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard
        )
    
    @admin_required
    @log_errors
    def delete_backup(self, message: types.Message, args: List[str] = None) -> None:
        """
        Обработчик команды /delete_backup.
        
        Args:
            message: Сообщение от пользователя
            args: Аргументы команды
        """
        try:
            # Отладка
            logger.info(f"delete_backup: исходный текст сообщения: '{message.text}'")
            logger.info(f"delete_backup: полученные аргументы: {args}")
            
            # Извлекаем аргументы из сообщения, если они не были переданы
            if args is None:
                args = self.extract_command_args(message.text)
                logger.info(f"delete_backup: аргументы после извлечения: {args}")
            
            # Проверяем наличие аргументов
            if not args or len(args) < 1:
                # Создаем клавиатуру с кнопкой "Назад"
                keyboard = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_backup"
                )
                keyboard.add(back_btn)
                
                # Если аргументы не переданы, отправляем информационное сообщение
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['info']} Введите команду в формате: <code>/delete_backup [имя_файла]</code>\n\n"
                    f"Например: <code>/delete_backup database_backup_2023-07-15.db</code>",
                    reply_markup=keyboard
                )
                return
            
            # Извлекаем имя файла резервной копии
            backup_filename = args[0]
            
            # Проверяем существование резервной копии
            backup_path = self.backup_service.get_backup_path(backup_filename)
            
            if not backup_path or not os.path.exists(backup_path):
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Резервная копия с именем '{backup_filename}' не найдена."
                )
                return
            
            # Запрашиваем подтверждение удаления
            confirm_markup = types.InlineKeyboardMarkup()
            confirm_button = types.InlineKeyboardButton(
                "Да, удалить",
                callback_data=f"delete_backup_{backup_filename}"
            )
            cancel_button = types.InlineKeyboardButton("Отмена", callback_data="cancel_delete")
            confirm_markup.add(confirm_button)
            confirm_markup.add(cancel_button)
            
            self.send_message(
                message.chat.id,
                f"{EMOJI['warning']} <b>Внимание!</b> Вы собираетесь удалить резервную копию '{backup_filename}'.\n\n"
                f"Это действие нельзя отменить. Вы уверены, что хотите продолжить?",
                reply_markup=confirm_markup
            )
            
        except Exception as e:
            logger.error(f"Ошибка при подготовке к удалению резервной копии: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    def confirm_delete(self, call: types.CallbackQuery) -> None:
        """
        Обработчик подтверждения удаления резервной копии.
        
        Args:
            call: Callback-запрос
        """
        try:
            # Извлекаем имя файла резервной копии
            backup_filename = call.data.split('_', 2)[2]
            
            # Отвечаем на callback-запрос
            self.bot.answer_callback_query(call.id)
            
            # Изменяем сообщение
            self.bot.edit_message_text(
                f"{EMOJI['process']} Удаление резервной копии '{backup_filename}'...",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=None
            )
            
            # Удаляем резервную копию
            result = self.backup_service.delete_backup(backup_filename)
            
            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_backup"
            )
            keyboard.add(back_btn)
            
            if result:
                self.bot.edit_message_text(
                    f"{EMOJI['success']} Резервная копия '{backup_filename}' успешно удалена.",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=keyboard
                )
                logger.info(f"Удалена резервная копия '{backup_filename}' администратором {call.from_user.id}")
            else:
                self.bot.edit_message_text(
                    f"{EMOJI['error']} <b>Ошибка:</b> Не удалось удалить резервную копию '{backup_filename}'.",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
                
        except Exception as e:
            logger.error(f"Ошибка при удалении резервной копии: {str(e)}")
            
            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_backup"
            )
            keyboard.add(back_btn)
            
            self.send_message(
                call.message.chat.id,
                f"{EMOJI['error']} <b>Ошибка при удалении:</b> {str(e)}",
                reply_markup=keyboard
            )
    
    @admin_required
    @log_errors
    def cancel_delete(self, call: types.CallbackQuery) -> None:
        """
        Обработчик отмены удаления резервной копии.
        
        Args:
            call: Callback-запрос
        """
        # Отвечаем на callback-запрос
        self.bot.answer_callback_query(call.id)
        
        # Создаем клавиатуру с кнопкой "Назад"
        keyboard = types.InlineKeyboardMarkup()
        back_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['back']} Назад", 
            callback_data="menu_backup"
        )
        keyboard.add(back_btn)
        
        # Изменяем сообщение
        self.bot.edit_message_text(
            f"{EMOJI['info']} Удаление резервной копии отменено.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard
        )
    
    @admin_required
    @log_errors
    def help_backup(self, message: types.Message) -> None:
        """
        Обработчик команды /help_backup.
        
        Args:
            message: Сообщение от пользователя
        """
        help_text = (
            f"{EMOJI['info']} <b>Справка по командам резервного копирования:</b>\n\n"
            f"/backup или /create_backup - Создать резервную копию базы данных\n"
            f"/get_backups или /list_backups - Получить список доступных резервных копий\n"
            f"/restore [имя_файла] - Восстановить базу данных из резервной копии\n"
            f"/delete_backup [имя_файла] - Удалить резервную копию\n"
            f"/help_backup - Показать эту справку\n\n"
            f"Также вы можете загрузить резервную копию, отправив файл с расширением .db боту."
        )
        
        # Создаем клавиатуру с кнопкой "Назад"
        keyboard = types.InlineKeyboardMarkup()
        back_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['back']} Назад", 
            callback_data="menu_backup"
        )
        keyboard.add(back_btn)
        
        self.send_message(message.chat.id, help_text, reply_markup=keyboard)
        logger.info(f"Отправлена справка по резервному копированию администратору {message.from_user.id}")
    
    @admin_required
    @log_errors
    def handle_document(self, message: types.Message) -> None:
        """
        Обработчик загрузки документа (для загрузки резервной копии).
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            # Проверяем, является ли пользователь администратором
            if not self.is_admin(message.from_user.id):
                return
            
            # Проверяем, является ли файл резервной копией
            if not message.document.file_name.endswith('.db'):
                return
            
            # Отправляем сообщение о начале загрузки
            self.send_message(
                message.chat.id,
                f"{EMOJI['process']} Загрузка резервной копии..."
            )
            
            # Получаем информацию о файле
            file_info = self.bot.get_file(message.document.file_id)
            downloaded_file = self.bot.download_file(file_info.file_path)
            
            # Сохраняем файл
            backup_path = self.backup_service.save_uploaded_backup(downloaded_file, message.document.file_name)
            
            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_backup"
            )
            keyboard.add(back_btn)
            
            if not backup_path or not os.path.exists(backup_path):
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Не удалось сохранить загруженную резервную копию.",
                    reply_markup=keyboard
                )
                return
            
            # Формируем сообщение об успешной загрузке
            success_message = (
                f"{EMOJI['success']} Резервная копия успешно загружена:\n\n"
                f"<b>Имя файла:</b> {message.document.file_name}\n"
                f"<b>Размер:</b> {message.document.file_size / 1024:.2f} KB\n\n"
                f"Для восстановления из этой резервной копии используйте команду:\n"
                f"<code>/restore {message.document.file_name}</code>"
            )
            
            self.send_message(message.chat.id, success_message, reply_markup=keyboard)
            logger.info(f"Загружена резервная копия '{message.document.file_name}' администратором {message.from_user.id}")
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке резервной копии: {str(e)}")
            
            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_backup"
            )
            keyboard.add(back_btn)
            
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка при загрузке резервной копии:</b> {str(e)}",
                reply_markup=keyboard
            )
    
    # Обработчики callback-запросов для команд в меню
    
    @log_errors
    def cmd_backup_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды backup.
        
        Args:
            call: Callback-запрос
        """
        # Проверяем, является ли пользователь администратором
        if not self.is_admin(call.from_user.id):
            self.bot.answer_callback_query(call.id, "У вас нет прав администратора для выполнения этой команды.")
            self.send_message(
                call.message.chat.id,
                "⚠️ У вас нет прав администратора для выполнения этой команды."
            )
            return

        # Отвечаем на callback-запрос
        self.bot.answer_callback_query(call.id, "Создание резервной копии...")
        
        try:
            # Отправляем сообщение о начале создания резервной копии
            self.send_message(
                call.message.chat.id,
                f"{EMOJI['loading']} Создание резервной копии базы данных..."
            )
            
            # Создаем резервную копию
            backup_path = self.backup_service.create_backup()
            
            if not backup_path or not os.path.exists(backup_path):
                # Создаем клавиатуру с кнопкой "Назад"
                keyboard = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="menu_backup"
                )
                keyboard.add(back_btn)
                
                self.send_message(
                    call.message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Не удалось создать резервную копию.",
                    reply_markup=keyboard
                )
                return
            
            # Получаем имя файла резервной копии
            backup_filename = os.path.basename(backup_path)
            backup_size = os.path.getsize(backup_path) / 1024  # размер в KB
            
            # Формируем сообщение об успешном создании резервной копии
            success_message = (
                f"{EMOJI['success']} Резервная копия успешно создана:\n\n"
                f"<b>Имя файла:</b> {backup_filename}\n"
                f"<b>Размер:</b> {backup_size:.2f} KB\n"
                f"<b>Дата создания:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
            )
            
            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_backup"
            )
            keyboard.add(back_btn)
            
            self.send_message(call.message.chat.id, success_message, reply_markup=keyboard)
            logger.info(f"Создана резервная копия базы данных администратором {call.from_user.id}: {backup_path}")
            
        except Exception as e:
            logger.error(f"Ошибка при создании резервной копии: {str(e)}")
            
            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_backup"
            )
            keyboard.add(back_btn)
            
            self.send_message(
                call.message.chat.id,
                f"{EMOJI['error']} <b>Ошибка при создании резервной копии:</b> {str(e)}",
                reply_markup=keyboard
            )
    
    @log_errors
    def cmd_get_backups_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды get_backups.
        
        Args:
            call: Callback-запрос
        """
        # Проверяем, является ли пользователь администратором
        if not self.is_admin(call.from_user.id):
            self.bot.answer_callback_query(call.id, "У вас нет прав администратора для выполнения этой команды.")
            self.send_message(
                call.message.chat.id,
                "⚠️ У вас нет прав администратора для выполнения этой команды."
            )
            return

        # Отвечаем на callback-запрос
        self.bot.answer_callback_query(call.id, "Получение списка резервных копий...")
        
        try:
            # Получаем список резервных копий
            backups = self.backup_service.get_backup_list()
            
            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_backup"
            )
            keyboard.add(back_btn)
            
            if not backups:
                self.send_message(
                    call.message.chat.id,
                    f"{EMOJI['info']} Резервных копий не найдено.",
                    reply_markup=keyboard
                )
                return
            
            # Формируем сообщение со списком резервных копий
            backups_text = f"{EMOJI['backup']} <b>Список резервных копий ({len(backups)}):</b>\n\n"
            
            for backup in backups:
                backup_name = backup.get('filename')
                backup_date = backup.get('created_at').strftime('%d.%m.%Y %H:%M:%S') if backup.get('created_at') else 'Неизвестно'
                backup_size = backup.get('size', 0) / 1024  # размер в KB
                
                backup_text = (
                    f"<b>{backup_name}</b>\n"
                    f"Дата создания: {backup_date}\n"
                    f"Размер: {backup_size:.2f} KB\n\n"
                )
                
                backups_text += backup_text
            
            # Добавляем инструкции
            backups_text += (
                f"Для восстановления из резервной копии используйте:\n"
                f"<code>/restore [имя_файла]</code>\n\n"
                f"Для удаления резервной копии используйте:\n"
                f"<code>/delete_backup [имя_файла]</code>"
            )
            
            self.send_message(call.message.chat.id, backups_text, reply_markup=keyboard)
            logger.info(f"Отправлен список резервных копий администратору {call.from_user.id}")
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка резервных копий: {str(e)}")
            
            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="menu_backup"
            )
            keyboard.add(back_btn)
            
            self.send_message(
                call.message.chat.id,
                f"{EMOJI['error']} <b>Ошибка при получении списка резервных копий:</b> {str(e)}",
                reply_markup=keyboard
            )
    
    @log_errors
    def cmd_restore_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды restore.
        
        Args:
            call: Callback-запрос
        """
        # Проверяем, является ли пользователь администратором
        if not self.is_admin(call.from_user.id):
            self.bot.answer_callback_query(call.id, "У вас нет прав администратора для выполнения этой команды.")
            self.send_message(
                call.message.chat.id,
                "⚠️ У вас нет прав администратора для выполнения этой команды."
            )
            return
            
        self.bot.answer_callback_query(call.id)
        
        # Создаем клавиатуру с кнопкой "Назад"
        keyboard = types.InlineKeyboardMarkup()
        back_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['back']} Назад", 
            callback_data="menu_backup"
        )
        keyboard.add(back_btn)
        
        self.send_message(
            call.message.chat.id,
            f"{EMOJI['info']} Введите команду в формате: <code>/restore [имя_файла]</code>\n\n"
            f"Например: <code>/restore database_backup_2023-07-15.db</code>",
            reply_markup=keyboard
        )
    
    @log_errors
    def cmd_delete_backup_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды delete_backup.
        
        Args:
            call: Callback-запрос
        """
        # Проверяем, является ли пользователь администратором
        if not self.is_admin(call.from_user.id):
            self.bot.answer_callback_query(call.id, "У вас нет прав администратора для выполнения этой команды.")
            self.send_message(
                call.message.chat.id,
                "⚠️ У вас нет прав администратора для выполнения этой команды."
            )
            return
            
        self.bot.answer_callback_query(call.id)
        
        # Создаем клавиатуру с кнопкой "Назад"
        keyboard = types.InlineKeyboardMarkup()
        back_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['back']} Назад", 
            callback_data="menu_backup"
        )
        keyboard.add(back_btn)
        
        self.send_message(
            call.message.chat.id,
            f"{EMOJI['info']} Введите команду в формате: <code>/delete_backup [имя_файла]</code>\n\n"
            f"Например: <code>/delete_backup database_backup_2023-07-15.db</code>",
            reply_markup=keyboard
        )
    
    @log_errors
    def cmd_help_backup_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды help_backup.
        
        Args:
            call: Callback-запрос
        """
        # Проверяем, является ли пользователь администратором
        if not self.is_admin(call.from_user.id):
            self.bot.answer_callback_query(call.id, "У вас нет прав администратора для выполнения этой команды.")
            self.send_message(
                call.message.chat.id,
                "⚠️ У вас нет прав администратора для выполнения этой команды."
            )
            return
            
        self.bot.answer_callback_query(call.id)
        
        # Текст справки
        help_text = (
            f"{EMOJI['info']} <b>Справка по командам резервного копирования:</b>\n\n"
            f"/backup или /create_backup - Создать резервную копию базы данных\n"
            f"/get_backups или /list_backups - Получить список доступных резервных копий\n"
            f"/restore [имя_файла] - Восстановить базу данных из резервной копии\n"
            f"/delete_backup [имя_файла] - Удалить резервную копию\n"
            f"/help_backup - Показать эту справку\n\n"
            f"Также вы можете загрузить резервную копию, отправив файл с расширением .db боту."
        )
        
        # Создаем клавиатуру с кнопкой "Назад"
        keyboard = types.InlineKeyboardMarkup()
        back_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['back']} Назад", 
            callback_data="menu_backup"
        )
        keyboard.add(back_btn)
        
        # Отправляем сообщение с кнопкой "Назад"
        self.send_message(call.message.chat.id, help_text, reply_markup=keyboard)
        logger.info(f"Отправлена справка по резервному копированию администратору {call.from_user.id}")
        
    def is_admin(self, user_id: int) -> bool:
        """
        Проверяет, является ли пользователь администратором.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True, если пользователь является администратором, иначе False
        """
        try:
            # Проверяем сначала в списке ADMIN_IDS для стандартных администраторов
            if user_id in ADMIN_IDS:
                return True
                
            # Проверяем в базе данных для динамически назначенных администраторов
            user = self.user_service.get_user_by_telegram_id(user_id)
            return user and user.is_admin
                
        except Exception as e:
            logger.error(f"Ошибка при проверке администратора: {str(e)}")
            return False 