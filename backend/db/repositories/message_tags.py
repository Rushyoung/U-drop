from db.repositories.base import RepositoryBase


class MessageTagRepository(RepositoryBase):
    def bind_tag(self, message_id: int, tag_id: int) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO messages_tags (message_id, tag_id) VALUES (?, ?)",
            (message_id, tag_id),
        )

    def bind_tags(self, message_id: int, tag_ids: list[int]) -> None:
        self.conn.executemany(
            "INSERT OR IGNORE INTO messages_tags (message_id, tag_id) VALUES (?, ?)",
            [(message_id, tag_id) for tag_id in tag_ids],
        )

    def list_tag_ids_by_message_id(self, message_id: int) -> list[int]:
        cursor = self.conn.execute("SELECT tag_id FROM messages_tags WHERE message_id = ?", (message_id,))
        return [row[0] for row in cursor.fetchall()]

    def delete_by_message_id(self, message_id: int) -> int:
        cursor = self.conn.execute("DELETE FROM messages_tags WHERE message_id = ?", (message_id,))
        return cursor.rowcount

    def delete_by_tag_id(self, tag_id: int) -> int:
        cursor = self.conn.execute("DELETE FROM messages_tags WHERE tag_id = ?", (tag_id,))
        return cursor.rowcount