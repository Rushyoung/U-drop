import sqlite3
from typing import List, Optional
from db.repositories.base import RepositoryBase

class AttachmentRepository(RepositoryBase):
    def add_attachment(
        self,
        message_id: int,
        file_hash: str,
        display_name: str,
        sort_order: int = 0
    ) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO attachments (message_id, file_hash, display_name, sort_order)
            VALUES (?, ?, ?, ?)
            """,
            (message_id, file_hash, display_name, sort_order)
        )
        # 联动：增加物理文件的引用计数
        self.conn.execute(
            "UPDATE file_info SET refer_count = refer_count + 1 WHERE full_hash = ?",
            (file_hash,)
        )
        return cursor.lastrowid

    def list_by_message_id(self, message_id: int) -> List[sqlite3.Row]:
        cursor = self.conn.execute(
            """
            SELECT a.*, f.file_size, f.mime_type, f.storage_path
            FROM attachments a
            JOIN file_info f ON a.file_hash = f.full_hash
            WHERE a.message_id = ?
            ORDER BY a.sort_order ASC
            """,
            (message_id,)
        )
        return cursor.fetchall()

    def list_by_message_ids(self, message_ids: List[int]) -> List[sqlite3.Row]:
        if not message_ids:
            return []
        placeholders = ",".join(["?"] * len(message_ids))
        cursor = self.conn.execute(
            f"""
            SELECT a.*, f.file_size, f.mime_type, f.storage_path
            FROM attachments a
            JOIN file_info f ON a.file_hash = f.full_hash
            WHERE a.message_id IN ({placeholders})
            ORDER BY a.message_id DESC, a.sort_order ASC
            """,
            message_ids
        )
        return cursor.fetchall()

    def get_attachment_by_id(self, attachment_id: int) -> Optional[sqlite3.Row]:
        """按 ID 获取附件详情"""
        cursor = self.conn.execute("SELECT * FROM attachments WHERE id = ?", (attachment_id,))
        return cursor.fetchone()

    def check_user_has_attachment(self, user_uuid: str, attachment_id: int) -> bool:
        """检查用户是否拥有该逻辑附件的所有权"""
        query = """
            SELECT 1 FROM attachments a
            JOIN messages m ON a.message_id = m.id
            WHERE m.sender_uuid = ? AND a.id = ?
            LIMIT 1
        """
        cursor = self.conn.execute(query, (user_uuid, attachment_id))
        return cursor.fetchone() is not None

    def delete_by_message_id(self, message_id: int):
        # 联动：减少物理文件的引用计数
        cursor = self.conn.execute("SELECT file_hash FROM attachments WHERE message_id = ?", (message_id,))
        rows = cursor.fetchall()
        for row in rows:
            self.conn.execute(
                "UPDATE file_info SET refer_count = refer_count - 1 WHERE full_hash = ?",
                (row['file_hash'],)
            )
        self.conn.execute("DELETE FROM attachments WHERE message_id = ?", (message_id,))

    def check_user_has_file(self, user_uuid: str, file_hash: str) -> bool:
        """检查用户是否已有该文件的引用（含已删除/回收站消息）"""
        query = """
            SELECT 1 FROM attachments a
            JOIN messages m ON a.message_id = m.id
            WHERE m.sender_uuid = ? AND a.file_hash = ?
            LIMIT 1
        """
        cursor = self.conn.execute(query, (user_uuid, file_hash))
        return cursor.fetchone() is not None

    def delete_attachment(self, attachment_id: int):
        """物理删除附件关联记录"""
        # 联动：减少物理文件的引用计数
        cursor = self.conn.execute("SELECT file_hash FROM attachments WHERE id = ?", (attachment_id,))
        row = cursor.fetchone()
        if row:
            self.conn.execute(
                "UPDATE file_info SET refer_count = refer_count - 1 WHERE full_hash = ?",
                (row['file_hash'],)
            )
            self.conn.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))
            return True
        return False

    def list_user_large_files(self, user_uuid: str, limit: int) -> List[sqlite3.Row]:
        """
        大文件猎手：获取用户占用的最大的文件，并聚合其引用详情。
        返回包含: full_hash, file_size, mime_type, refer_count, 
        以及拼接好的引用字符串 "msg_id:attach_id:display_name|..."
        """
        query = """
            SELECT 
                f.full_hash, f.file_size, f.mime_type, f.refer_count,
                GROUP_CONCAT(m.id || ':' || a.id || ':' || a.display_name, '|') as ref_info
            FROM file_info f
            JOIN attachments a ON f.full_hash = a.file_hash
            JOIN messages m ON a.message_id = m.id
            WHERE m.sender_uuid = ? AND m.deleted_at IS NULL
            GROUP BY f.full_hash
            ORDER BY f.file_size DESC
            LIMIT ?
        """
        cursor = self.conn.execute(query, (user_uuid, limit))
        return cursor.fetchall()
