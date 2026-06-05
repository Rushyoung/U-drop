-- U-Drop 数据库初始化脚本 (SQLite)
-- 编码: UTF-8

PRAGMA foreign_keys = ON;

-- 1. 用户表
CREATE TABLE IF NOT EXISTS users (
    uuid TEXT PRIMARY KEY,               -- 用户唯一标识 (UUID)
    account TEXT NOT NULL UNIQUE,         -- 登录账号
    password_hash TEXT NOT NULL,          -- 加盐哈希值（argon2）
    created_at INTEGER NOT NULL,           -- 注册时间戳
    expire_set INTEGER NOT NULL            --设置登陆过期时间（天）
);

-- 2. 设备表
CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,           -- 设备唯一标识
    user_uuid TEXT NOT NULL,              -- 所属用户
    device_type INTEGER NOT NULL,         -- 0:Web, 1:Android
    device_name TEXT,                     -- 设备名称
    last_seen INTEGER,                    -- 最后活跃时间
    FOREIGN KEY (user_uuid) REFERENCES users(uuid) ON DELETE CASCADE
);

-- 3. 文件信息表 (内容寻址存储核心)
CREATE TABLE IF NOT EXISTS file_info (
    full_hash TEXT PRIMARY KEY,           -- 全量哈希 (Blake3)
    sparse_hash TEXT,                     -- 快速哈希 (头中尾MD5)
    file_name TEXT NOT NULL,              -- 原始文件名
    file_size BIGINT NOT NULL,            -- 文件大小 (Bytes)
    mime_type TEXT,                       -- 文件类型
    storage_path TEXT NOT NULL,           -- 存储路径 (WebDAV或本地)
    refer_count INTEGER DEFAULT 1         -- 引用计数 (用于物理清理)
);
CREATE INDEX IF NOT EXISTS idx_file_sparse_hash ON file_info(sparse_hash);

-- 4. 消息/时间线表
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_uuid TEXT NOT NULL,
    device_id TEXT NOT NULL,
    type INTEGER NOT NULL,                -- 0:文本, 1:图片, 2:文件
    content TEXT,                         -- 文本内容或消息描述
    file_hash TEXT,                       -- 关联文件哈希 (可选)
    timestamp INTEGER NOT NULL,           -- 发送时间戳
    deleted_at INTEGER,                   -- 软删除时间戳 (NULL:正常, >0:已删除)
    FOREIGN KEY (sender_uuid) REFERENCES users(uuid) ON DELETE CASCADE,
    FOREIGN KEY (device_id) REFERENCES devices(device_id),
    FOREIGN KEY (file_hash) REFERENCES file_info(full_hash)
);
CREATE INDEX IF NOT EXISTS idx_msg_timestamp ON messages(timestamp); -- 缓冲刷新优化
CREATE INDEX IF NOT EXISTS idx_msg_lookup ON messages(sender_uuid, deleted_at, id DESC); -- 滑动窗口查询优化

-- 5. 活跃会话表
CREATE TABLE IF NOT EXISTS sessions (
    bearer_token TEXT PRIMARY KEY,
    user_uuid TEXT NOT NULL,
    device_id TEXT,
    expire_time INTEGER NOT NULL,
    is_single_use INTEGER DEFAULT 0,      -- 一次性标记 (0:长效, 1:用后即焚)
    FOREIGN KEY (user_uuid) REFERENCES users(uuid) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_session_user ON sessions(user_uuid);
CREATE INDEX IF NOT EXISTS idx_session_expire ON sessions(expire_time);
CREATE INDEX IF NOT EXISTS idx_session_user_device ON sessions(user_uuid, device_id);

-- 6. 标签表 (修正表名为 hashtags)
CREATE TABLE IF NOT EXISTS hashtags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_uuid TEXT NOT NULL,
    tag_name TEXT NOT NULL,
    FOREIGN KEY (user_uuid) REFERENCES users(uuid) ON DELETE CASCADE,
    UNIQUE(user_uuid, tag_name)           -- 同一用户下标签名唯一
);
CREATE INDEX IF NOT EXISTS idx_msg_deleted_at ON messages(deleted_at);
-- 7. 消息-标签关联表
CREATE TABLE IF NOT EXISTS messages_tags (
    message_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (message_id, tag_id),
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES hashtags(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_mt_tag ON messages_tags(tag_id);

-- [预留] 上传任务表
-- 当前计划以内存态维护（如 dict），此表保留为备份/恢复用途
CREATE TABLE IF NOT EXISTS upload_tasks (
    upload_id TEXT PRIMARY KEY,
    user_uuid TEXT NOT NULL,
    temp_path TEXT NOT NULL,
    received_size BIGINT DEFAULT 0,
    total_size BIGINT NOT NULL,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (user_uuid) REFERENCES users(uuid) ON DELETE CASCADE
);

-- 8. 泛型分享中心表 (Universal Share Center)
CREATE TABLE IF NOT EXISTS shares (
    share_id TEXT PRIMARY KEY,            -- 随机生成的短码或UUID
    creator_uuid TEXT NOT NULL,           -- 创建者
    target_type TEXT NOT NULL,            -- 资源类型 ('file', 'message', 'tag_timeline' 等)
    target_payload TEXT NOT NULL,         -- 资源标识或规则 (如 file_hash)
    expire_time INTEGER,                  -- 到期时间戳 (NULL 永久)
    max_uses INTEGER DEFAULT 0,           -- 最大使用次数 (0 表示无限制，>0 即单次/有限次)
    use_count INTEGER DEFAULT 0,          -- 已使用次数
    password_hash TEXT,                   -- 提取码哈希 (可选)
    created_at INTEGER NOT NULL,
    FOREIGN KEY (creator_uuid) REFERENCES users(uuid) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_share_expire ON shares(expire_time);
