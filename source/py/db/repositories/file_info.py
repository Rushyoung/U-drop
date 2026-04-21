import sqlite3

from db.repositories.base import RepositoryBase


class FileInfoRepository(RepositoryBase):
    def upsert_file(
        self,
        full_hash: str,
        sparse_hash: str | None,
        file_name: str,
        file_size: int,
        mime_type: str | None,
        storage_path: str,
        thumbnail_url: str | None,
        refer_count: int = 1,
    ) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO file_info (
                full_hash, sparse_hash, file_name, file_size, mime_type, storage_path, thumbnail_url, refer_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (full_hash, sparse_hash, file_name, file_size, mime_type, storage_path, thumbnail_url, refer_count),
        )

    def get_by_full_hash(self, full_hash: str) -> sqlite3.Row | None:
        cursor = self.conn.execute("SELECT * FROM file_info WHERE full_hash = ?", (full_hash,))
        return cursor.fetchone()

    def get_by_sparse_hash(self, sparse_hash: str) -> list[sqlite3.Row]:
        cursor = self.conn.execute("SELECT * FROM file_info WHERE sparse_hash = ?", (sparse_hash,))
        return cursor.fetchall()

    def increase_refer_count(self, full_hash: str, step: int = 1) -> int:
        cursor = self.conn.execute(
            "UPDATE file_info SET refer_count = refer_count + ? WHERE full_hash = ?",
            (step, full_hash),
        )
        return cursor.rowcount

    def decrease_refer_count(self, full_hash: str, step: int = 1) -> int:
        cursor = self.conn.execute(
            "UPDATE file_info SET refer_count = refer_count - ? WHERE full_hash = ?",
            (step, full_hash),
        )
        return cursor.rowcount

    def update_thumbnail_url(self, full_hash: str, thumbnail_url: str) -> int:
        cursor = self.conn.execute(
            "UPDATE file_info SET thumbnail_url = ? WHERE full_hash = ?",
            (thumbnail_url, full_hash),
        )
        return cursor.rowcount