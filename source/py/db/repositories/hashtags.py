import sqlite3

from db.repositories.base import RepositoryBase


class HashtagRepository(RepositoryBase):
    def create_tag(self, user_uuid: str, tag_name: str) -> int:
        cursor = self.conn.execute(
            "INSERT INTO hashtags (user_uuid, tag_name) VALUES (?, ?)",
            (user_uuid, tag_name),
        )
        return cursor.lastrowid

    def get_by_id(self, tag_id: int) -> sqlite3.Row | None:
        cursor = self.conn.execute("SELECT * FROM hashtags WHERE id = ?", (tag_id,))
        return cursor.fetchone()

    def get_by_user_and_name(self, user_uuid: str, tag_name: str) -> sqlite3.Row | None:
        cursor = self.conn.execute(
            "SELECT * FROM hashtags WHERE user_uuid = ? AND tag_name = ?",
            (user_uuid, tag_name),
        )
        return cursor.fetchone()

    def list_by_user_uuid(self, user_uuid: str) -> list[sqlite3.Row]:
        cursor = self.conn.execute("SELECT * FROM hashtags WHERE user_uuid = ?", (user_uuid,))
        return cursor.fetchall()

    def delete_tag(self, tag_id: int) -> int:
        cursor = self.conn.execute("DELETE FROM hashtags WHERE id = ?", (tag_id,))
        return cursor.rowcount