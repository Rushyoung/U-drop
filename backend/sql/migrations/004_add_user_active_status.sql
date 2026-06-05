-- Migration: Add user active status
ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1;
