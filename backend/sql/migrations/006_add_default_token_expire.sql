-- Migration: Add default token expire setting
INSERT OR IGNORE INTO sys_settings (key, value) VALUES ('default_token_expire', '86400'); -- 默认 1 天
