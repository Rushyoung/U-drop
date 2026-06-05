-- U-Drop 数据库初始化脚本 v2 (解耦重构版)
-- 编码: UTF-8

PRAGMA foreign_keys = ON;

-- 1. 用户表
CREATE TABLE IF NOT EXISTS users (
    uuid TEXT PRIMARY KEY,               -- 用户唯一标识 (UUID)
    account TEXT NOT NULL UNIQUE,         -- 登录账号
    password_hash TEXT NOT NULL,          -- 加盐哈希值（argon2）
    role TEXT DEFAULT 'user',             -- 用户角色: admin, user
    is_active INTEGER DEFAULT 1,          -- 是否启用: 1启用, 0禁用
    created_at INTEGER NOT NULL,          -- 注册时间
    temp_expire_hours INTEGER DEFAULT 24, -- 临时 Session 有效小时数 (<= 24)
    sliding_window_days INTEGER DEFAULT 30 -- 滑动窗口续期天数
);

-- 1.1 系统全局设置表
CREATE TABLE IF NOT EXISTS sys_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
INSERT OR IGNORE INTO sys_settings (key, value) VALUES ('allow_registration', 'true');
INSERT OR IGNORE INTO sys_settings (key, value) VALUES ('auth_rate_limit', '5');

-- 2. 设备管理表
CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,           -- 设备唯一标识 (前端生成)
    user_uuid TEXT NOT NULL,              -- 所属用户
    device_type INTEGER NOT NULL,         -- 0:Web, 1:Android, 2:PC
    device_name TEXT,                     -- 设备名称 (如: My Pixel 8)
    last_seen INTEGER NOT NULL,           -- 最后在线时间
    FOREIGN KEY (user_uuid) REFERENCES users(uuid) ON DELETE CASCADE
);

-- 3. 物理文件信息表 (不包含业务属性)
CREATE TABLE IF NOT EXISTS file_info (
    full_hash TEXT PRIMARY KEY,           -- 文件全量哈希 (Blake3)
    sparse_hash TEXT,                     -- 快速哈希 (头中尾MD5)
    file_size BIGINT NOT NULL,            -- 文件大小 (Bytes)
    mime_type TEXT,                       -- 文件类型
    storage_path TEXT NOT NULL,           -- 存储路径 (local://xxx)
    refer_count INTEGER DEFAULT 0         -- 物理引用计数 (由附件表维护)
);
CREATE INDEX IF NOT EXISTS idx_file_sparse_hash ON file_info(sparse_hash);

-- 4. 消息/时间线主表 (轻量化)
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_uuid TEXT NOT NULL,
    device_id TEXT NOT NULL,
    type INTEGER NOT NULL,                -- 0:文本, 1:混合/附件
    content TEXT,                         -- 文本内容
    timestamp INTEGER NOT NULL,           -- 发送时间戳
    deleted_at INTEGER,                   -- 软删除时间戳 (NULL:正常)
    FOREIGN KEY (sender_uuid) REFERENCES users(uuid) ON DELETE CASCADE,
    FOREIGN KEY (device_id) REFERENCES devices(device_id)
);
CREATE INDEX IF NOT EXISTS idx_msg_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_msg_lookup ON messages(sender_uuid, deleted_at, id DESC);

-- 5. 消息附件表 (解耦层)
CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,          -- 关联的消息
    file_hash TEXT NOT NULL,              -- 关联的文件物理哈希
    display_name TEXT NOT NULL,           -- 在该消息中显示的文件名
    sort_order INTEGER DEFAULT 0,         -- 多附件排序
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
    FOREIGN KEY (file_hash) REFERENCES file_info(full_hash)
);
CREATE INDEX IF NOT EXISTS idx_attach_msg_id ON attachments(message_id);
CREATE INDEX IF NOT EXISTS idx_attach_file_hash ON attachments(file_hash);

-- 6. 标签定义表
CREATE TABLE IF NOT EXISTS hashtags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_uuid TEXT NOT NULL,
    tag_name TEXT NOT NULL,
    FOREIGN KEY (user_uuid) REFERENCES users(uuid) ON DELETE CASCADE,
    UNIQUE(user_uuid, tag_name)
);

-- 7. 消息-标签关联表
CREATE TABLE IF NOT EXISTS messages_tags (
    message_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (message_id, tag_id),
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES hashtags(id) ON DELETE CASCADE
);

-- 8. 活跃会话表
CREATE TABLE IF NOT EXISTS sessions (
    bearer_token TEXT PRIMARY KEY,
    user_uuid TEXT NOT NULL,
    device_id TEXT,
    expire_time INTEGER NOT NULL,
    is_single_use INTEGER DEFAULT 0,
    is_sliding INTEGER DEFAULT 0,         -- 是否开启滑动窗口续期
    FOREIGN KEY (user_uuid) REFERENCES users(uuid) ON DELETE CASCADE
);

-- 9. 泛型分享表
CREATE TABLE IF NOT EXISTS shares (
    share_id TEXT PRIMARY KEY,
    creator_uuid TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_payload TEXT NOT NULL,         -- 若是file则存哈希，若是timeline则存配置
    display_name TEXT,                    -- 分享时固化的显示名称
    expire_time INTEGER,
    max_uses INTEGER DEFAULT 0,
    use_count INTEGER DEFAULT 0,
    password_hash TEXT,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (creator_uuid) REFERENCES users(uuid) ON DELETE CASCADE
);

-- 10. 版本管理表 (迁移引擎用)
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at INTEGER NOT NULL
);
