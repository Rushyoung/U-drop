import sqlite3

from db.repositories.base import RepositoryBase


class UploadTaskRepository(RepositoryBase):
    def create_task(
        self,
        upload_id: str,
        user_uuid: str,
        temp_path: str,
        received_size: int,
        total_size: int,
        created_at: int,
        message_id: int | None = None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO upload_tasks (upload_id, user_uuid, temp_path, received_size, total_size, created_at, message_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (upload_id, user_uuid, temp_path, received_size, total_size, created_at, message_id),
        )

    def get_by_upload_id(self, upload_id: str) -> sqlite3.Row | None:
        cursor = self.conn.execute("SELECT * FROM upload_tasks WHERE upload_id = ?", (upload_id,))
        return cursor.fetchone()

    def update_received_size(self, upload_id: str, received_size: int) -> int:
        cursor = self.conn.execute(
            "UPDATE upload_tasks SET received_size = ? WHERE upload_id = ?",
            (received_size, upload_id),
        )
        return cursor.rowcount

    def delete_task(self, upload_id: str) -> int:
        cursor = self.conn.execute("DELETE FROM upload_tasks WHERE upload_id = ?", (upload_id,))
        return cursor.rowcount

    def list_by_user_uuid(self, user_uuid: str) -> list[sqlite3.Row]:
        cursor = self.conn.execute("SELECT * FROM upload_tasks WHERE user_uuid = ?", (user_uuid,))
        return cursor.fetchall()