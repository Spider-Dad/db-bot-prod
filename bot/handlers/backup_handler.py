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
from bot.constants import EMOJI, ERROR_MESSAGES
from .base_handler import BaseHandler
from .decorators import admin_required, log_errors, command_args

logger = logging.getLogger(__name__)


class BackupHandler(BaseHandler):
    """
    Обработчик команд для управления резервными копиями базы данных.
    
    Обрабатывает команды, связанные с созданием и восстановлением
    резервных копий базы данных.
    """
    
    def __init__(self, bot: telebot.TeleBot, backup_service: BackupService):
        """
        Инициализация обработчика резервного копирования.
        
        Args:
            bot: Экземпляр бота Telegram
            backup_service: Сервис для работы с резервными копиями
        """
        super().__init__(bot)
        self.backup_service = backup_service
        
    def register_handlers(self) -> None:
        """Регистрация обработчиков команд для управления резервными копиями."""
        # Команды для работы с резервными копиями
        self.bot.message_handler(commands=['backup'])(self.create_backup)
        self.bot.message_handler(commands=['get_backups'])(self.get_backups)
        self.bot.message_handler(commands=['restore'])(self.restore_backup)
        self.bot.message_handler(commands=['delete_backup'])(self.delete_backup)
        self.bot.message_handler(commands=['download_backup'])(self.download_backup)
        self.bot.message_handler(commands=['help_backup'])(self.help_backup)
        
        # Обработчики документов (для загрузки резервных копий)
        self.bot.message_handler(content_types=['document'])(self.handle_document)
        
        # Обработчики callback-запросов
        self.bot.callback_query_handler(func=lambda call: call.data.startswith('restore_'))(self.confirm_restore)
        self.bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_restore'))(self.cancel_restore)
        self.bot.callback_query_handler(func=lambda call: call.data.startswith('delete_backup_'))(self.confirm_delete)
        self.bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_delete'))(self.cancel_delete)
        
        # Обработчики для команд в меню
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_backup')(self.cmd_backup_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_get_backups')(self.cmd_get_backups_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_restore')(self.cmd_restore_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_delete_backup')(self.cmd_delete_backup_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_download_backup')(self.cmd_download_backup_callback)
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
                f"{EMOJI['process']} Создание резервной копии базы данных..."
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
                f"<b>Дата создания:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
                f"Используйте команду /download_backup {backup_filename} для скачивания резервной копии."
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
                f"Для скачивания резервной копии используйте:\n"
                f"<code>/download_backup [имя_файла]</code>\n\n"
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
    @command_args(1)
    def restore_backup(self, message: types.Message, args: List[str]) -> None:
        """
        Обработчик команды /restore.
        
        Args:
            message: Сообщение от пользователя
            args: Аргументы команды
        """
        try:
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
            
            if result:
                self.bot.edit_message_text(
                    f"{EMOJI['success']} База данных успешно восстановлена из резервной копии '{backup_filename}'.",
                    call.message.chat.id,
                    call.message.message_id
                )
                logger.info(f"Восстановлена база данных из резервной копии '{backup_filename}' администратором {call.from_user.id}")
            else:
                self.bot.edit_message_text(
                    f"{EMOJI['error']} <b>Ошибка:</b> Не удалось восстановить базу данных из резервной копии '{backup_filename}'.",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML'
                )
                
        except Exception as e:
            logger.error(f"Ошибка при восстановлении из резервной копии: {str(e)}")
            self.send_message(
                call.message.chat.id,
                f"{EMOJI['error']} <b>Ошибка при восстановлении:</b> {str(e)}"
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
        
        # Изменяем сообщение
        self.bot.edit_message_text(
            f"{EMOJI['info']} Восстановление из резервной копии отменено.",
            call.message.chat.id,
            call.message.message_id
        )
    
    @admin_required
    @log_errors
    @command_args(1)
    def delete_backup(self, message: types.Message, args: List[str]) -> None:
        """
        Обработчик команды /delete_backup.
        
        Args:
            message: Сообщение от пользователя
            args: Аргументы команды
        """
        try:
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
            
            if result:
                self.bot.edit_message_text(
                    f"{EMOJI['success']} Резервная копия '{backup_filename}' успешно удалена.",
                    call.message.chat.id,
                    call.message.message_id
                )
                logger.info(f"Удалена резервная копия '{backup_filename}' администратором {call.from_user.id}")
            else:
                self.bot.edit_message_text(
                    f"{EMOJI['error']} <b>Ошибка:</b> Не удалось удалить резервную копию '{backup_filename}'.",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='HTML'
                )
                
        except Exception as e:
            logger.error(f"Ошибка при удалении резервной копии: {str(e)}")
            self.send_message(
                call.message.chat.id,
                f"{EMOJI['error']} <b>Ошибка при удалении:</b> {str(e)}"
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
        
        # Изменяем сообщение
        self.bot.edit_message_text(
            f"{EMOJI['info']} Удаление резервной копии отменено.",
            call.message.chat.id,
            call.message.message_id
        )
    
    @admin_required
    @log_errors
    @command_args(1)
    def download_backup(self, message: types.Message, args: List[str]) -> None:
        """
        Обработчик команды /download_backup.
        
        Args:
            message: Сообщение от пользователя
            args: Аргументы команды
        """
        try:
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
            
            # Отправляем файл резервной копии
            with open(backup_path, 'rb') as backup_file:
                self.bot.send_document(
                    message.chat.id,
                    backup_file,
                    caption=f"{EMOJI['backup']} Резервная копия базы данных: {backup_filename}"
                )
                
            logger.info(f"Отправлена резервная копия '{backup_filename}' администратору {message.from_user.id}")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке резервной копии: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка при отправке резервной копии:</b> {str(e)}"
            )
    
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
            
            if not backup_path or not os.path.exists(backup_path):
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Не удалось сохранить загруженную резервную копию."
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
            
            self.send_message(message.chat.id, success_message)
            logger.info(f"Загружена резервная копия '{message.document.file_name}' администратором {message.from_user.id}")
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке резервной копии: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка при загрузке резервной копии:</b> {str(e)}"
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
            f"/backup - Создать резервную копию базы данных\n"
            f"/get_backups - Получить список доступных резервных копий\n"
            f"/restore [имя_файла] - Восстановить базу данных из резервной копии\n"
            f"/delete_backup [имя_файла] - Удалить резервную копию\n"
            f"/download_backup [имя_файла] - Скачать резервную копию\n\n"
            f"Также вы можете загрузить резервную копию, отправив файл с расширением .db боту."
        )
        self.send_message(message.chat.id, help_text)
        logger.info(f"Отправлена справка по резервному копированию администратору {message.from_user.id}")

    # Обработчики callback-запросов для команд в меню
    
    @log_errors
    def cmd_backup_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды backup.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.create_backup(call.message)
    
    @log_errors
    def cmd_get_backups_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды get_backups.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.get_backups(call.message)
    
    @log_errors
    def cmd_restore_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды restore.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.send_message(
            call.message.chat.id,
            f"{EMOJI['info']} Введите команду в формате: <code>/restore [имя_файла]</code>\n\n"
            f"Например: <code>/restore database_backup_2023-07-15.db</code>"
        )
    
    @log_errors
    def cmd_delete_backup_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды delete_backup.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.send_message(
            call.message.chat.id,
            f"{EMOJI['info']} Введите команду в формате: <code>/delete_backup [имя_файла]</code>\n\n"
            f"Например: <code>/delete_backup database_backup_2023-07-15.db</code>"
        )
    
    @log_errors
    def cmd_download_backup_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды download_backup.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.send_message(
            call.message.chat.id,
            f"{EMOJI['info']} Введите команду в формате: <code>/download_backup [имя_файла]</code>\n\n"
            f"Например: <code>/download_backup database_backup_2023-07-15.db</code>"
        )
    
    @log_errors
    def cmd_help_backup_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды help_backup.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.help_backup(call.message)
        
    def is_admin(self, user_id: int) -> bool:
        """
        Проверяет, является ли пользователь администратором.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True, если пользователь является администратором, иначе False
        """
        try:
            # Здесь можно добавить логику проверки администратора
            # Для текущей реализации, она вынесена в декоратор admin_required
            return True
        except Exception as e:
            logger.error(f"Ошибка при проверке администратора: {str(e)}")
            return False 