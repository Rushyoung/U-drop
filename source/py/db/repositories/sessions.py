import sqlite3

from db.repositories.base import RepositoryBase


class SessionRepository(RepositoryBase):
    def create_session(
        self,
        bearer_token: str,
        user_uuid: str,
        device_id: str | None,
        expire_time: int,
    ) -> None:
        self.conn.execute(
            "INSERT INTO sessions (bearer_token, user_uuid, device_id, expire_time) VALUES (?, ?, ?, ?)",
            (bearer_token, user_uuid, device_id, expire_time),
        )

    def get_by_token(self, bearer_token: str) -> sqlite3.Row | None:
        cursor = self.conn.execute("SELECT * FROM sessions WHERE bearer_token = ?", (bearer_token,))
        return cursor.fetchone()

    def delete_by_token(self, bearer_token: str) -> int:
        cursor = self.conn.execute("DELETE FROM sessions WHERE bearer_token = ?", (bearer_token,))
        return cursor.rowcount

    def delete_by_user_uuid(self, user_uuid: str) -> int:
        cursor = self.conn.execute("DELETE FROM sessions WHERE user_uuid = ?", (user_uuid,))
        return cursor.rowcount

    def list_expired(self, now: int) -> list[sqlite3.Row]:
        cursor = self.conn.execute("SELECT * FROM sessions WHERE expire_time < ?", (now,))
        return cursor.fetchall()