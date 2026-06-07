import sqlite3
from db.repositories.base import RepositoryBase

class FileInfoRepository(RepositoryBase):
    def upsert_file(
        self,
        full_hash: str,
        sparse_hash: str | None,
        file_size: int,
        mime_type: str | None,
        storage_path: str,
        refer_count: int = 0, # 重构后初始化通常为 0，由附件表增加
    ) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO file_info (
                full_hash, sparse_hash, file_size, mime_type, storage_path, refer_count
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (full_hash, sparse_hash, file_size, mime_type, storage_path, refer_count),
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

    def list_orphans(self) -> list[sqlite3.Row]:
        """获取所有引用计数归零的物理文件记录"""
        cursor = self.conn.execute("SELECT * FROM file_info WHERE refer_count <= 0")
        return cursor.fetchall()

    def delete_file_info(self, full_hash: str) -> int:
        """从数据库物理删除文件记录"""
        cursor = self.conn.execute("DELETE FROM file_info WHERE full_hash = ?", (full_hash,))
        return cursor.rowcount
