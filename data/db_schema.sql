CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT NOT NULL,
    last_name TEXT,
    birth_date TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT 0,
    is_subscribed BOOLEAN DEFAULT 0,
    is_notifications_enabled BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notification_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    message_text TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL,
    error_message TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS notification_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    template TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'birthday',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

CREATE TABLE IF NOT EXISTS notification_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL,
    days_before INTEGER NOT NULL,
    time TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (template_id) REFERENCES notification_templates(id)
);

CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO system_settings (key, value, description) 
VALUES ('payment_phone', '7 920 132 2534', 'Номер телефона для перевода');

INSERT OR IGNORE INTO system_settings (key, value, description) 
VALUES ('payment_name', 'Диана Ибрагимовна Рыжова', 'ФИО получателя платежа');

-- Добавление столбца updated_at, если он отсутствует
PRAGMA foreign_keys=off;

-- Проверка и добавление столбца в таблицу users
SELECT CASE 
  WHEN NOT EXISTS(SELECT 1 FROM pragma_table_info('users') WHERE name='updated_at') THEN
    ('ALTER TABLE users ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
  ELSE
    ('SELECT 1')
END;

-- Проверка и добавление столбца в таблицу notification_logs
SELECT CASE 
  WHEN NOT EXISTS(SELECT 1 FROM pragma_table_info('notification_logs') WHERE name='updated_at') THEN
    ('ALTER TABLE notification_logs ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
  ELSE
    ('SELECT 1')
END;

-- Проверка и добавление столбца в таблицу notification_settings
SELECT CASE 
  WHEN NOT EXISTS(SELECT 1 FROM pragma_table_info('notification_settings') WHERE name='updated_at') THEN
    ('ALTER TABLE notification_settings ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
  ELSE
    ('SELECT 1')
END;

PRAGMA foreign_keys=on;