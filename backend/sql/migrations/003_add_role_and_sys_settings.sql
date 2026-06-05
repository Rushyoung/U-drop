-- Migration: Add user role and system settings table
ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user';

CREATE TABLE IF NOT EXISTS sys_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Initialize default settings
INSERT OR IGNORE INTO sys_settings (key, value) VALUES ('allow_registration', 'true');
