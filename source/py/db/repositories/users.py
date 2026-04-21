import sqlite3

from db.repositories.base import RepositoryBase
from schemas.auth import UserInternal
from typing import Optional

class UserRepository(RepositoryBase):
    def create_user(self, uuid: str, account: str, password_hash: str, created_at: int, expire_set:int = 1) -> None:
        self.conn.execute(
            "INSERT INTO users (uuid, account, password_hash, created_at, expire_set) VALUES (?, ?, ?, ?, ?)",
            (uuid, account, password_hash, created_at, expire_set),
        )

    def get_by_uuid(self, uuid: str) -> Optional[UserInternal]:
        cursor = self.conn.execute("SELECT * FROM users WHERE uuid = ?", (uuid,))
        row = cursor.fetchone()
        return UserInternal.model_validate(dict(row)) if row else None

    def get_by_account(self, account: str) -> Optional[UserInternal]:
        cursor = self.conn.execute("SELECT * FROM users WHERE account = ?", (account,))
        row = cursor.fetchone()
        return UserInternal.model_validate(dict(row)) if row else None
    
    def check_account(self, account: str) -> bool:
        cursor = self.conn.execute(
            "SELECT 1 FROM users WHERE account = ? LIMIT 1",
            (account,),
        )
        return cursor.fetchone() is not None
    
    def update_password_hash(self, uuid: str, password_hash: str) -> int:
        cursor = self.conn.execute(
            "UPDATE users SET password_hash = ? WHERE uuid = ?",
            (password_hash, uuid),
        )
        return cursor.rowcount

    def delete_user(self, uuid: str) -> int:
        cursor = self.conn.execute("DELETE FROM users WHERE uuid = ?", (uuid,))
        return cursor.rowcount