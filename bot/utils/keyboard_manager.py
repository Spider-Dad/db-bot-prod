"""
Менеджер клавиатур для бота.

Этот модуль содержит класс KeyboardManager, отвечающий за создание
различных типов клавиатур для интерфейса бота.
"""

import logging
from telebot import types
from bot.constants import EMOJI

logger = logging.getLogger(__name__)

class KeyboardManager:
    """
    Менеджер клавиатур для бота.
    
    Предоставляет методы для создания различных типов клавиатур
    для взаимодействия пользователя с ботом.
    """
    
    @staticmethod
    def create_main_menu(is_admin: bool = False) -> types.InlineKeyboardMarkup:
        """
        Создает основное меню бота.
        
        Args:
            is_admin: Флаг, указывающий, является ли пользователь администратором
            
        Returns:
            types.InlineKeyboardMarkup: Объект клавиатуры с кнопками основного меню
        """
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        # Основные кнопки для всех пользователей
        birthdays_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['gift']} Дни рождения", 
            callback_data="menu_birthdays"
        )
        game_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['game']} Игра 2048", 
            callback_data="menu_game"
        )
        write_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['pencil']} ПишиЛегко", 
            callback_data="menu_write"
        )
        
        # Добавляем основные кнопки
        keyboard.add(birthdays_btn)
        keyboard.add(game_btn, write_btn)
        
        # Дополнительные кнопки для администраторов
        if is_admin:
            users_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['users']} Пользователи", 
                callback_data="menu_users"
            )
            templates_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['templates']} Шаблоны", 
                callback_data="menu_templates"
            )
            notifications_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['bell']} Рассылки", 
                callback_data="menu_notifications"
            )
            backup_btn = types.InlineKeyboardButton(
                text=f"{EMOJI['backup']} Резервные копии", 
                callback_data="menu_backup"
            )
            
            # Добавляем административные кнопки
            keyboard.add(users_btn, templates_btn)
            keyboard.add(notifications_btn, backup_btn)
        
        return keyboard
    
    @staticmethod
    def create_users_menu() -> types.InlineKeyboardMarkup:
        """
        Создает меню управления пользователями.
        
        Returns:
            types.InlineKeyboardMarkup: Объект клавиатуры с кнопками управления пользователями
        """
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        
        # Кнопки для управления пользователями
        add_user_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['plus']} Добавить пользователя", 
            callback_data="cmd_add_user"
        )
        remove_user_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['minus']} Удалить пользователя", 
            callback_data="cmd_remove_user"
        )
        users_dir_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['directory']} Справочник пользователей", 
            callback_data="cmd_users_directory"
        )
        set_admin_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['admin']} Назначить администратора", 
            callback_data="cmd_set_admin"
        )
        remove_admin_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['user']} Отозвать права администратора", 
            callback_data="cmd_remove_admin"
        )
        back_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['back']} Назад", 
            callback_data="menu_main"
        )
        
        # Добавляем кнопки
        keyboard.add(add_user_btn)
        keyboard.add(remove_user_btn)
        keyboard.add(users_dir_btn)
        keyboard.add(set_admin_btn)
        keyboard.add(remove_admin_btn)
        keyboard.add(back_btn)
        
        return keyboard
    
    @staticmethod
    def create_templates_menu() -> types.InlineKeyboardMarkup:
        """
        Создает меню управления шаблонами.
        
        Returns:
            types.InlineKeyboardMarkup: Объект клавиатуры с кнопками управления шаблонами
        """
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        
        # Кнопки для управления шаблонами
        add_template_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['plus']} Добавить шаблон", 
            callback_data="cmd_add_template"
        )
        remove_template_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['minus']} Удалить шаблон", 
            callback_data="cmd_remove_template"
        )
        templates_list_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['list']} Список шаблонов", 
            callback_data="cmd_templates_list"
        )
        update_template_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['edit']} Обновить шаблон", 
            callback_data="cmd_update_template"
        )
        preview_template_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['eye']} Предпросмотр шаблона", 
            callback_data="cmd_preview_template"
        )
        activate_template_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['check']} Активировать шаблон", 
            callback_data="cmd_activate_template"
        )
        deactivate_template_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['cross']} Деактивировать шаблон", 
            callback_data="cmd_deactivate_template"
        )
        template_help_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['help']} Помощь по шаблонам", 
            callback_data="cmd_template_help"
        )
        back_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['back']} Назад", 
            callback_data="menu_main"
        )
        
        # Добавляем кнопки
        keyboard.add(add_template_btn)
        keyboard.add(remove_template_btn)
        keyboard.add(templates_list_btn)
        keyboard.add(update_template_btn)
        keyboard.add(preview_template_btn)
        keyboard.add(activate_template_btn)
        keyboard.add(deactivate_template_btn)
        keyboard.add(template_help_btn)
        keyboard.add(back_btn)
        
        return keyboard
    
    @staticmethod
    def create_notifications_menu() -> types.InlineKeyboardMarkup:
        """
        Создает меню управления рассылками.
        
        Returns:
            types.InlineKeyboardMarkup: Объект клавиатуры с кнопками управления рассылками
        """
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        
        # Кнопки для управления рассылками
        settings_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['setting']} Настройки уведомлений", 
            callback_data="menu_settings"
        )
        send_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['send']} Отправить произвольное уведомление", 
            callback_data="cmd_send_notification"
        )
        back_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['back']} Назад", 
            callback_data="menu_main"
        )
        
        # Добавляем кнопки
        keyboard.add(settings_btn)
        keyboard.add(send_btn)
        keyboard.add(back_btn)
        
        return keyboard
    
    @staticmethod
    def create_settings_menu() -> types.InlineKeyboardMarkup:
        """
        Создает меню управления настройками уведомлений.
        
        Returns:
            types.InlineKeyboardMarkup: Объект клавиатуры с кнопками управления настройками
        """
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        # Кнопки для основных действий с настройками
        list_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['list']} Список настроек", 
            callback_data="cmd_get_settings"
        )
        add_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['plus']} Добавить настройку", 
            callback_data="cmd_set_setting"
        )
        update_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['edit']} Изменить настройку", 
            callback_data="cmd_update_setting"
        )
        remove_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['minus']} Удалить настройку", 
            callback_data="cmd_delete_setting"
        )
        
        # Кнопки для активации/деактивации
        activate_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['check']} Активировать", 
            callback_data="cmd_activate_setting"
        )
        deactivate_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['cross']} Деактивировать", 
            callback_data="cmd_deactivate_setting"
        )
        
        # Кнопка справки
        help_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['help']} Справка", 
            callback_data="cmd_help_settings"
        )
        
        # Кнопка возврата в меню рассылок
        back_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['back']} Назад", 
            callback_data="menu_notifications"
        )
        
        # Добавляем кнопки в клавиатуру
        keyboard.add(list_btn, add_btn)
        keyboard.add(update_btn, remove_btn)
        keyboard.add(activate_btn, deactivate_btn)
        keyboard.add(help_btn)
        keyboard.add(back_btn)
        
        return keyboard
    
    @staticmethod
    def create_backup_menu() -> types.InlineKeyboardMarkup:
        """
        Создает меню управления резервными копиями.
        
        Returns:
            types.InlineKeyboardMarkup: Объект клавиатуры с кнопками управления резервными копиями
        """
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        
        # Кнопки для управления резервными копиями
        create_backup_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['save']} Создать резервную копию", 
            callback_data="cmd_create_backup"
        )
        restore_backup_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['restore']} Восстановить из копии", 
            callback_data="cmd_restore_backup"
        )
        list_backups_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['list']} Список копий", 
            callback_data="cmd_list_backups"
        )
        delete_backup_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['delete']} Удалить копию", 
            callback_data="cmd_delete_backup"
        )
        back_btn = types.InlineKeyboardButton(
            text=f"{EMOJI['back']} Назад", 
            callback_data="menu_main"
        )
        
        # Добавляем кнопки
        keyboard.add(create_backup_btn)
        keyboard.add(restore_backup_btn)
        keyboard.add(list_backups_btn)
        keyboard.add(delete_backup_btn)
        keyboard.add(back_btn)
        
        return keyboard 