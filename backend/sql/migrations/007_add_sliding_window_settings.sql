-- Migration: Add sliding window support and refactor expire_set
-- 1. Rename expire_set to temp_expire_hours and set default to 24
ALTER TABLE users RENAME COLUMN expire_set TO temp_expire_hours;
UPDATE users SET temp_expire_hours = temp_expire_hours * 24; -- Convert days to hours
ALTER TABLE users ADD COLUMN sliding_window_days INTEGER DEFAULT 30;

-- 2. Add is_sliding to sessions
ALTER TABLE sessions ADD COLUMN is_sliding INTEGER DEFAULT 0;
