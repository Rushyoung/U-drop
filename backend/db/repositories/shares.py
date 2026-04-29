import sqlite3
from typing import Optional
from db.repositories.base import RepositoryBase

class ShareRepository(RepositoryBase):
    def create_share(
        self,
        share_id: str,
        creator_uuid: str,
        target_type: str,
        target_payload: str,
        display_name: Optional[str],
        expire_time: Optional[int],
        max_uses: int,
        password_hash: Optional[str],
        created_at: int
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO shares (
                share_id, creator_uuid, target_type, target_payload, display_name,
                expire_time, max_uses, password_hash, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (share_id, creator_uuid, target_type, target_payload, display_name,
             expire_time, max_uses, password_hash, created_at)
        )

    def get_share(self, share_id: str) -> Optional[sqlite3.Row]:
        cursor = self.conn.execute("SELECT * FROM shares WHERE share_id = ?", (share_id,))
        return cursor.fetchone()

    def consume_share_atomic(self, share_id: str) -> bool:
        """原子化消耗分享次数：仅在未达上限或无限制时更新"""
        query = """
            UPDATE shares 
            SET use_count = use_count + 1 
            WHERE share_id = ? 
            AND (max_uses = 0 OR use_count < max_uses)
        """
        cursor = self.conn.execute(query, (share_id,))
        return cursor.rowcount > 0

    def delete_share(self, share_id: str) -> int:
        cursor = self.conn.execute("DELETE FROM shares WHERE share_id = ?", (share_id,))
        return cursor.rowcount

    def list_by_user(self, user_uuid: str) -> list[sqlite3.Row]:
        """列出该用户创建的所有分享，并关联文件物理大小"""
        query = """
            SELECT s.*, f.file_size 
            FROM shares s
            LEFT JOIN file_info f ON s.target_type = 'file' AND s.target_payload = f.full_hash
            WHERE s.creator_uuid = ? 
            ORDER BY s.created_at DESC
        """
        cursor = self.conn.execute(query, (user_uuid,))
        return cursor.fetchall()
