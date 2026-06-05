-- Migration: Add auth rate limit setting
INSERT OR IGNORE INTO sys_settings (key, value) VALUES ('auth_rate_limit', '5');
