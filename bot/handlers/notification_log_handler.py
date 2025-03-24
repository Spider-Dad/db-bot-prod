"""
Обработчики команд для управления журналом уведомлений.

Этот модуль содержит обработчики для команд бота,
связанных с просмотром и управлением журналом отправленных уведомлений.
"""

import logging
import telebot
from telebot import types
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

from bot.services.notification_log_service import NotificationLogService
from bot.constants import EMOJI, ERROR_MESSAGES
from .base_handler import BaseHandler
from .decorators import admin_required, log_errors, command_args

logger = logging.getLogger(__name__)


class NotificationLogHandler(BaseHandler):
    """
    Обработчик команд для управления журналом уведомлений.
    
    Обрабатывает команды, связанные с просмотром и управлением
    журналом отправленных уведомлений.
    """
    
    def __init__(self, bot: telebot.TeleBot, log_service: NotificationLogService):
        """
        Инициализация обработчика журнала уведомлений.
        
        Args:
            bot: Экземпляр бота Telegram
            log_service: Сервис для работы с журналом уведомлений
        """
        super().__init__(bot)
        self.log_service = log_service
        
    def register_handlers(self) -> None:
        """Регистрация обработчиков команд для управления журналом уведомлений."""
        # Команды для работы с журналом уведомлений
        self.bot.message_handler(commands=['get_logs'])(self.get_logs)
        self.bot.message_handler(commands=['get_user_logs'])(self.get_user_logs)
        self.bot.message_handler(commands=['get_template_logs'])(self.get_template_logs)
        self.bot.message_handler(commands=['get_logs_stats'])(self.get_logs_stats)
        self.bot.message_handler(commands=['clear_old_logs'])(self.clear_old_logs)
        self.bot.message_handler(commands=['help_logs'])(self.help_logs)
        
        # Обработчики callback-запросов для команд
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_get_logs')(self.cmd_get_logs_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_get_user_logs')(self.cmd_get_user_logs_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_get_template_logs')(self.cmd_get_template_logs_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_get_logs_stats')(self.cmd_get_logs_stats_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_clear_old_logs')(self.cmd_clear_old_logs_callback)
        self.bot.callback_query_handler(func=lambda call: call.data == 'cmd_help_logs')(self.cmd_help_logs_callback)
    
    @admin_required
    @log_errors
    def get_logs(self, message: types.Message) -> None:
        """
        Обработчик команды /get_logs.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            # Проверяем, указано ли количество последних записей
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            limit = 10  # По умолчанию показываем 10 записей
            
            if args and args[0].isdigit():
                limit = int(args[0])
                # Ограничиваем максимальное количество записей
                if limit > 50:
                    limit = 50
                    self.send_message(
                        message.chat.id,
                        f"{EMOJI['info']} Ограничено до 50 последних записей."
                    )
            
            # Получаем последние записи из журнала
            logs = self.log_service.get_recent_logs(limit)
            
            if not logs:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['info']} В журнале нет записей."
                )
                return
            
            # Формируем сообщение со списком записей
            logs_text = f"{EMOJI['log']} <b>Последние {len(logs)} записей журнала уведомлений:</b>\n\n"
            
            for log in logs:
                log_id = log.get('id')
                user_id = log.get('user_id')
                user_name = log.get('user_name', 'Неизвестный пользователь')
                template_id = log.get('template_id')
                template_name = log.get('template_name', 'Неизвестный шаблон')
                timestamp = log.get('timestamp', '')
                status = log.get('status', 'unknown')
                
                status_emoji = EMOJI['success'] if status == 'success' else EMOJI['error']
                
                # Форматируем timestamp
                try:
                    dt = datetime.fromisoformat(timestamp)
                    timestamp_str = dt.strftime('%d.%m.%Y %H:%M:%S')
                except:
                    timestamp_str = timestamp
                
                log_text = (
                    f"{status_emoji} <b>ID {log_id}</b> - {timestamp_str}\n"
                    f"Получатель: {user_name} (ID: {user_id})\n"
                    f"Шаблон: {template_name} (ID: {template_id})\n"
                    f"Статус: {status}\n\n"
                )
                
                logs_text += log_text
            
            self.send_message(message.chat.id, logs_text)
            logger.info(f"Отправлен список записей журнала администратору {message.from_user.id}")
            
        except Exception as e:
            logger.error(f"Ошибка при получении записей журнала: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    @command_args(1)
    def get_user_logs(self, message: types.Message, args: List[str]) -> None:
        """
        Обработчик команды /get_user_logs.
        
        Args:
            message: Сообщение от пользователя
            args: Аргументы команды
        """
        try:
            # Извлекаем ID пользователя
            try:
                user_id = int(args[0])
            except ValueError:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> ID пользователя должен быть числом."
                )
                return
            
            # Определяем лимит записей (если указан)
            limit = 10
            if len(args) > 1 and args[1].isdigit():
                limit = int(args[1])
                if limit > 50:
                    limit = 50
                    self.send_message(
                        message.chat.id,
                        f"{EMOJI['info']} Ограничено до 50 последних записей."
                    )
            
            # Получаем записи журнала для пользователя
            logs = self.log_service.get_logs_by_user_id(user_id, limit)
            
            if not logs:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['info']} В журнале нет записей для пользователя с ID {user_id}."
                )
                return
            
            # Формируем сообщение со списком записей
            user_name = logs[0].get('user_name', f'Пользователь {user_id}')
            logs_text = f"{EMOJI['log']} <b>Последние {len(logs)} уведомлений для {user_name}:</b>\n\n"
            
            for log in logs:
                log_id = log.get('id')
                template_id = log.get('template_id')
                template_name = log.get('template_name', 'Неизвестный шаблон')
                timestamp = log.get('timestamp', '')
                status = log.get('status', 'unknown')
                
                status_emoji = EMOJI['success'] if status == 'success' else EMOJI['error']
                
                # Форматируем timestamp
                try:
                    dt = datetime.fromisoformat(timestamp)
                    timestamp_str = dt.strftime('%d.%m.%Y %H:%M:%S')
                except:
                    timestamp_str = timestamp
                
                log_text = (
                    f"{status_emoji} <b>ID {log_id}</b> - {timestamp_str}\n"
                    f"Шаблон: {template_name} (ID: {template_id})\n"
                    f"Статус: {status}\n\n"
                )
                
                logs_text += log_text
            
            self.send_message(message.chat.id, logs_text)
            logger.info(f"Отправлен список записей журнала для пользователя {user_id} администратору {message.from_user.id}")
            
        except Exception as e:
            logger.error(f"Ошибка при получении записей журнала пользователя: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    @command_args(1)
    def get_template_logs(self, message: types.Message, args: List[str]) -> None:
        """
        Обработчик команды /get_template_logs.
        
        Args:
            message: Сообщение от пользователя
            args: Аргументы команды
        """
        try:
            # Извлекаем ID шаблона
            try:
                template_id = int(args[0])
            except ValueError:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> ID шаблона должен быть числом."
                )
                return
            
            # Определяем лимит записей (если указан)
            limit = 10
            if len(args) > 1 and args[1].isdigit():
                limit = int(args[1])
                if limit > 50:
                    limit = 50
                    self.send_message(
                        message.chat.id,
                        f"{EMOJI['info']} Ограничено до 50 последних записей."
                    )
            
            # Получаем записи журнала для шаблона
            logs = self.log_service.get_logs_by_template_id(template_id, limit)
            
            if not logs:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['info']} В журнале нет записей для шаблона с ID {template_id}."
                )
                return
            
            # Формируем сообщение со списком записей
            template_name = logs[0].get('template_name', f'Шаблон {template_id}')
            logs_text = f"{EMOJI['log']} <b>Последние {len(logs)} уведомлений с шаблоном \"{template_name}\":</b>\n\n"
            
            for log in logs:
                log_id = log.get('id')
                user_id = log.get('user_id')
                user_name = log.get('user_name', 'Неизвестный пользователь')
                timestamp = log.get('timestamp', '')
                status = log.get('status', 'unknown')
                
                status_emoji = EMOJI['success'] if status == 'success' else EMOJI['error']
                
                # Форматируем timestamp
                try:
                    dt = datetime.fromisoformat(timestamp)
                    timestamp_str = dt.strftime('%d.%m.%Y %H:%M:%S')
                except:
                    timestamp_str = timestamp
                
                log_text = (
                    f"{status_emoji} <b>ID {log_id}</b> - {timestamp_str}\n"
                    f"Получатель: {user_name} (ID: {user_id})\n"
                    f"Статус: {status}\n\n"
                )
                
                logs_text += log_text
            
            self.send_message(message.chat.id, logs_text)
            logger.info(f"Отправлен список записей журнала для шаблона {template_id} администратору {message.from_user.id}")
            
        except Exception as e:
            logger.error(f"Ошибка при получении записей журнала шаблона: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    def get_logs_stats(self, message: types.Message) -> None:
        """
        Обработчик команды /get_logs_stats.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            # Получаем статистику за разные периоды
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            this_week = today - timedelta(days=today.weekday())
            this_month = today.replace(day=1)
            
            # Статистика за сегодня
            today_stats = self.log_service.get_logs_stats_by_date(today)
            # Статистика за вчера
            yesterday_stats = self.log_service.get_logs_stats_by_date(yesterday)
            # Статистика за неделю
            week_stats = self.log_service.get_logs_stats_by_period(this_week, today)
            # Статистика за месяц
            month_stats = self.log_service.get_logs_stats_by_period(this_month, today)
            # Общая статистика
            total_stats = self.log_service.get_logs_stats()
            
            # Формируем сообщение со статистикой
            stats_text = f"{EMOJI['stats']} <b>Статистика уведомлений:</b>\n\n"
            
            # Сегодня
            stats_text += f"<b>Сегодня ({today.strftime('%d.%m.%Y')}):</b>\n"
            stats_text += f"Всего: {today_stats.get('total', 0)}\n"
            stats_text += f"Успешно: {today_stats.get('success', 0)}\n"
            stats_text += f"Ошибок: {today_stats.get('failed', 0)}\n\n"
            
            # Вчера
            stats_text += f"<b>Вчера ({yesterday.strftime('%d.%m.%Y')}):</b>\n"
            stats_text += f"Всего: {yesterday_stats.get('total', 0)}\n"
            stats_text += f"Успешно: {yesterday_stats.get('success', 0)}\n"
            stats_text += f"Ошибок: {yesterday_stats.get('failed', 0)}\n\n"
            
            # За неделю
            stats_text += f"<b>За неделю ({this_week.strftime('%d.%m.%Y')} - {today.strftime('%d.%m.%Y')}):</b>\n"
            stats_text += f"Всего: {week_stats.get('total', 0)}\n"
            stats_text += f"Успешно: {week_stats.get('success', 0)}\n"
            stats_text += f"Ошибок: {week_stats.get('failed', 0)}\n\n"
            
            # За месяц
            stats_text += f"<b>За месяц ({this_month.strftime('%d.%m.%Y')} - {today.strftime('%d.%m.%Y')}):</b>\n"
            stats_text += f"Всего: {month_stats.get('total', 0)}\n"
            stats_text += f"Успешно: {month_stats.get('success', 0)}\n"
            stats_text += f"Ошибок: {month_stats.get('failed', 0)}\n\n"
            
            # Всего
            stats_text += f"<b>Всего за всё время:</b>\n"
            stats_text += f"Всего: {total_stats.get('total', 0)}\n"
            stats_text += f"Успешно: {total_stats.get('success', 0)}\n"
            stats_text += f"Ошибок: {total_stats.get('failed', 0)}\n"
            
            self.send_message(message.chat.id, stats_text)
            logger.info(f"Отправлена статистика уведомлений администратору {message.from_user.id}")
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики уведомлений: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    @admin_required
    @log_errors
    @command_args(1)
    def clear_old_logs(self, message: types.Message, args: List[str]) -> None:
        """
        Обработчик команды /clear_old_logs.
        
        Args:
            message: Сообщение от пользователя
            args: Аргументы команды
        """
        try:
            # Извлекаем количество дней
            try:
                days = int(args[0])
                if days < 1:
                    raise ValueError("Количество дней должно быть положительным числом")
            except ValueError:
                self.send_message(
                    message.chat.id,
                    f"{EMOJI['error']} <b>Ошибка:</b> Количество дней должно быть положительным числом."
                )
                return
            
            # Запрашиваем подтверждение перед удалением
            confirm_markup = types.InlineKeyboardMarkup()
            confirm_button = types.InlineKeyboardButton(
                f"Да, удалить записи старше {days} дней",
                callback_data=f"confirm_clear_logs_{days}"
            )
            cancel_button = types.InlineKeyboardButton("Отмена", callback_data="cancel_clear_logs")
            confirm_markup.add(confirm_button)
            confirm_markup.add(cancel_button)
            
            self.send_message(
                message.chat.id,
                f"{EMOJI['warning']} <b>Внимание!</b> Вы собираетесь удалить все записи журнала старше {days} дней.\n\n"
                f"Это действие нельзя отменить. Вы уверены?",
                reply_markup=confirm_markup
            )
            
            # Регистрируем обработчики для кнопок подтверждения
            self.bot.callback_query_handler(
                func=lambda call: call.data == f"confirm_clear_logs_{days}"
            )(lambda call: self._confirm_clear_logs(call, days))
            
            self.bot.callback_query_handler(
                func=lambda call: call.data == "cancel_clear_logs"
            )(self._cancel_clear_logs)
            
        except Exception as e:
            logger.error(f"Ошибка при подготовке к очистке журнала: {str(e)}")
            self.send_message(
                message.chat.id,
                f"{EMOJI['error']} <b>Ошибка:</b> {str(e)}"
            )
    
    def _confirm_clear_logs(self, call: types.CallbackQuery, days: int) -> None:
        """
        Обработчик подтверждения очистки старых записей журнала.
        
        Args:
            call: Callback-запрос
            days: Количество дней
        """
        try:
            self.bot.answer_callback_query(call.id)
            
            # Определяем дату, до которой нужно удалить записи
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Удаляем старые записи
            deleted_count = self.log_service.clear_old_logs(days)
            
            # Сообщаем о результате
            self.bot.edit_message_text(
                f"{EMOJI['success']} Удалено {deleted_count} записей журнала старше {cutoff_date.strftime('%d.%m.%Y')}.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=None
            )
            
            logger.info(f"Удалено {deleted_count} записей журнала старше {days} дней администратором {call.from_user.id}")
            
        except Exception as e:
            logger.error(f"Ошибка при очистке журнала: {str(e)}")
            self.send_message(
                call.message.chat.id,
                f"{EMOJI['error']} <b>Ошибка при очистке журнала:</b> {str(e)}"
            )
    
    def _cancel_clear_logs(self, call: types.CallbackQuery) -> None:
        """
        Обработчик отмены очистки старых записей журнала.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.bot.edit_message_text(
            f"{EMOJI['info']} Очистка журнала отменена.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=None
        )
    
    @admin_required
    @log_errors
    def help_logs(self, message: types.Message) -> None:
        """
        Обработчик команды /help_logs.
        
        Args:
            message: Сообщение от пользователя
        """
        help_text = (
            f"{EMOJI['info']} <b>Справка по командам журнала уведомлений:</b>\n\n"
            f"/get_logs [количество] - Получить последние записи журнала уведомлений\n"
            f"/get_user_logs [id_пользователя] [количество] - Получить записи для конкретного пользователя\n"
            f"/get_template_logs [id_шаблона] [количество] - Получить записи для конкретного шаблона\n"
            f"/get_logs_stats - Получить статистику уведомлений\n"
            f"/clear_old_logs [дней] - Удалить записи журнала старше указанного количества дней\n"
        )
        self.send_message(message.chat.id, help_text)
        logger.info(f"Отправлена справка по журналу уведомлений администратору {message.from_user.id}")

    # Обработчики callback-запросов
    
    @log_errors
    def cmd_get_logs_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды get_logs.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.get_logs(call.message)
    
    @log_errors
    def cmd_get_user_logs_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды get_user_logs.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.send_message(
            call.message.chat.id,
            f"{EMOJI['info']} Введите команду в формате: <code>/get_user_logs [id_пользователя] [количество]</code>\n\n"
            f"Например: <code>/get_user_logs 123456789 20</code>"
        )
    
    @log_errors
    def cmd_get_template_logs_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды get_template_logs.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.send_message(
            call.message.chat.id,
            f"{EMOJI['info']} Введите команду в формате: <code>/get_template_logs [id_шаблона] [количество]</code>\n\n"
            f"Например: <code>/get_template_logs 1 20</code>"
        )
    
    @log_errors
    def cmd_get_logs_stats_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды get_logs_stats.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.get_logs_stats(call.message)
    
    @log_errors
    def cmd_clear_old_logs_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды clear_old_logs.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.send_message(
            call.message.chat.id,
            f"{EMOJI['info']} Введите команду в формате: <code>/clear_old_logs [дней]</code>\n\n"
            f"Например: <code>/clear_old_logs 30</code>"
        )
    
    @log_errors
    def cmd_help_logs_callback(self, call: types.CallbackQuery) -> None:
        """
        Обработчик callback-запроса для команды help_logs.
        
        Args:
            call: Callback-запрос
        """
        self.bot.answer_callback_query(call.id)
        self.help_logs(call.message) 