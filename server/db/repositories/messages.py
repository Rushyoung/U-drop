import sqlite3
import time
from core.config import settings
from core.logger import logger
from db.repositories.base import RepositoryBase


class MessageRepository(RepositoryBase):
    def create_message(
        self,
        sender_uuid: str,
        device_id: str,
        message_type: int,
        content: str | None,
        timestamp: int,
    ) -> int:
        """创建基础消息 (不包含附件)"""
        cursor = self.conn.execute(
            """
            INSERT INTO messages (sender_uuid, device_id, type, content, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (sender_uuid, device_id, message_type, content, timestamp),
        )
        logger.debug(f"消息id：{cursor.lastrowid}|消息插入：{sender_uuid, device_id, message_type, content, timestamp}")

        return cursor.lastrowid

    def get_by_id(self, message_id: int) -> sqlite3.Row | None:
        cursor = self.conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
        return cursor.fetchone()

    def list_messages(
        self,
        user_uuid: str,
        limit: int = 50,
        anchor_id: int | None = None,
        mode: str = "initial",
        keyword: str | None = None,
        hashtag: str | None = None,
    ) -> list[sqlite3.Row]:
        """
        高性能消息列表拉取 (滑动窗口逻辑)
        """
        base_filter = "WHERE m.sender_uuid = ? AND m.deleted_at IS NULL"
        params = [user_uuid]

        if keyword:
            # 安全增强：转义 LIKE 通配符，防止注入攻击
            safe_keyword = keyword.replace("/", "//").replace("%", "/%").replace("_", "/_")
            base_filter += " AND m.content LIKE ? ESCAPE '/'"
            params.append(f"%{safe_keyword}%")
        if hashtag:
            base_filter += """ AND EXISTS (
                SELECT 1 FROM messages_tags mt JOIN hashtags h ON mt.tag_id = h.id
                WHERE mt.message_id = m.id AND h.tag_name = ?
            )"""
            params.append(hashtag)

        if mode == "initial" and anchor_id is not None:
            # 向上探测步长：确保至少包含锚点本身 (limit // 2 + 1)
            # 这样即使 limit=1，也能正确找到锚点
            forward_limit = (limit // 2) + 1
            window_params = params + params + [anchor_id, forward_limit, limit]

            query = f"""
                SELECT m.*, d.device_name, d.device_type 
                FROM messages m
                JOIN devices d ON m.device_id = d.device_id
                {base_filter}
                AND m.id <= (
                    SELECT MAX(id) FROM (
                        SELECT m.id FROM messages m 
                        {base_filter} AND m.id >= ? 
                        ORDER BY m.id ASC LIMIT ?
                    )
                )
                ORDER BY m.id DESC LIMIT ?
            """
            cursor = self.conn.execute(query, window_params)
            return cursor.fetchall()

        query = f"""
            SELECT m.*, d.device_name, d.device_type 
            FROM messages m
            JOIN devices d ON m.device_id = d.device_id
            {base_filter}
        """
        
        if anchor_id is not None:
            if mode == "before":
                query += " AND m.id < ?"
                params.append(anchor_id)
            elif mode == "after":
                query += " AND m.id > ?"
                params.append(anchor_id)

        query += " ORDER BY m.id DESC LIMIT ?"
        params.append(limit)

        cursor = self.conn.execute(query, params)
        return cursor.fetchall()

    def soft_delete_message(self, message_id: int) -> int:
        now = int(time.time())
        cursor = self.conn.execute(
            "UPDATE messages SET deleted_at = ? WHERE id = ?",
            (now, message_id),
        )
        return cursor.rowcount
    
    def clean_trash(self, trash_days: int = settings.TRASH_EXPIRE_TIME) -> int:
        threshold = int(time.time()) - (trash_days * 86400)
        cursor = self.conn.execute(
            "DELETE FROM messages WHERE deleted_at < ?",
            (threshold, )
        )
        return cursor.rowcount

    def list_trash(self, user_uuid: str) -> list[sqlite3.Row]:
        """获取用户回收站内的消息列表"""
        query = """
            SELECT m.*, d.device_name, d.device_type 
            FROM messages m
            JOIN devices d ON m.device_id = d.device_id
            WHERE m.sender_uuid = ? AND m.deleted_at IS NOT NULL
            ORDER BY m.deleted_at DESC
        """
        cursor = self.conn.execute(query, (user_uuid,))
        return cursor.fetchall()

    def restore_message(self, message_id: int) -> int:
        """从回收站恢复"""
        cursor = self.conn.execute(
            "UPDATE messages SET deleted_at = NULL WHERE id = ?",
            (message_id,)
        )
        return cursor.rowcount

    def list_expired_for_user(self, user_uuid: str, days: int) -> list[sqlite3.Row]:
        """寻找特定用户已超期的废件"""
        threshold = int(time.time()) - (days * 86400)
        cursor = self.conn.execute(
            "SELECT id FROM messages WHERE sender_uuid = ? AND deleted_at < ?",
            (user_uuid, threshold)
        )
        return cursor.fetchall()

    def hard_delete_message(self, message_id: int) -> int:
        """彻底物理删除单条消息"""
        cursor = self.conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))
        return cursor.rowcount

    def get_user_trash_ids(self, user_uuid: str) -> list[int]:
        """获取用户回收站中所有消息的 ID"""
        cursor = self.conn.execute("SELECT id FROM messages WHERE sender_uuid = ? AND deleted_at IS NOT NULL", (user_uuid,))
        return [row[0] for row in cursor.fetchall()]
