import sqlite3

from db.repositories.base import RepositoryBase


class SessionRepository(RepositoryBase):
    def create_session(
        self,
        bearer_token: str,
        user_uuid: str,
        device_id: str | None,
        expire_time: int,
        is_single_use: int = 0,
        is_sliding: int = 0,
    ) -> None:
        self.conn.execute(
            "INSERT INTO sessions (bearer_token, user_uuid, device_id, expire_time, is_single_use, is_sliding) VALUES (?, ?, ?, ?, ?, ?)",
            (bearer_token, user_uuid, device_id, expire_time, is_single_use, is_sliding),
        )

    def get_by_token(self, bearer_token: str) -> sqlite3.Row | None:
        cursor = self.conn.execute("SELECT * FROM sessions WHERE bearer_token = ?", (bearer_token,))
        return cursor.fetchone()

    def get_by_user_and_device(self, user_uuid: str, device_id: str) -> sqlite3.Row | None:
        """根据用户ID和设备ID查询唯一的会话Token"""
        cursor = self.conn.execute(
            "SELECT * FROM sessions WHERE user_uuid = ? AND device_id = ?",
            (user_uuid, device_id)
        )
        return cursor.fetchone()

    def delete_by_token(self, bearer_token: str) -> int:
        cursor = self.conn.execute("DELETE FROM sessions WHERE bearer_token = ?", (bearer_token,))
        return cursor.rowcount

    def delete_by_user_uuid(self, user_uuid: str) -> int:
        cursor = self.conn.execute("DELETE FROM sessions WHERE user_uuid = ?", (user_uuid,))
        return cursor.rowcount

    def delete_by_device_id(self, device_id: str) -> int:
        """删除特定设备的所有活跃会话"""
        cursor = self.conn.execute("DELETE FROM sessions WHERE device_id = ?", (device_id,))
        return cursor.rowcount

    def list_expired(self, now: int) -> list[sqlite3.Row]:
        cursor = self.conn.execute("SELECT * FROM sessions WHERE expire_time < ?", (now,))
        return cursor.fetchall()