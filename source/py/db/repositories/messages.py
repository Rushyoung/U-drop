import sqlite3

from db.repositories.base import RepositoryBase


class MessageRepository(RepositoryBase):
    def create_message(
        self,
        sender_uuid: str,
        device_id: str,
        message_type: int,
        content: str | None,
        file_hash: str | None,
        timestamp: int,
    ) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO messages (sender_uuid, device_id, type, content, file_hash, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (sender_uuid, device_id, message_type, content, file_hash, timestamp),
        )
        return cursor.lastrowid

    def get_by_id(self, message_id: int) -> sqlite3.Row | None:
        cursor = self.conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
        return cursor.fetchone()

    def list_messages(
        self,
        limit: int,
        offset: int = 0,
        keyword: str | None = None,
        hashtag: str | None = None,
    ) -> list[sqlite3.Row]:
        query = "SELECT * FROM messages WHERE is_deleted = 0"
        params = []

        if keyword:
            query += " AND content LIKE ?"
            params.append(f"%{keyword}%")

        if hashtag:
            query += """
                AND id IN (
                    SELECT mt.message_id
                    FROM messages_tags mt
                    JOIN hashtags h ON mt.tag_id = h.id
                    WHERE h.tag_name = ?
                )
            """
            params.append(hashtag)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = self.conn.execute(query, params)
        return cursor.fetchall()

    def soft_delete_message(self, message_id: int) -> int:
        cursor = self.conn.execute(
            "UPDATE messages SET is_deleted = 1 WHERE id = ?",
            (message_id,),
        )
        return cursor.rowcount

    def update_file_hash(self, message_id: int, file_hash: str) -> int:
        cursor = self.conn.execute(
            "UPDATE messages SET file_hash = ? WHERE id = ?",
            (file_hash, message_id),
        )
        return cursor.rowcount