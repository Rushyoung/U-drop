import sqlite3
from db.repositories.base import RepositoryBase
from schemas.auth import UserInternal
from typing import Optional

class UserRepository(RepositoryBase):
    def create_user(self, uuid: str, account: str, password_hash: str, created_at: int, temp_expire_hours: int = 24, sliding_window_days: int = 30, role: str = 'user', is_active: int = 1) -> None:
        self.conn.execute(
            "INSERT INTO users (uuid, account, password_hash, created_at, temp_expire_hours, sliding_window_days, role, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (uuid, account, password_hash, created_at, temp_expire_hours, sliding_window_days, role, is_active),
        )

    def has_admin(self) -> bool:
        """判断系统是否已存在管理员"""
        cursor = self.conn.execute("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1")
        return cursor.fetchone() is not None

    def get_by_uuid(self, uuid: str) -> Optional[UserInternal]:
        cursor = self.conn.execute("SELECT * FROM users WHERE uuid = ?", (uuid,))
        row = cursor.fetchone()
        return UserInternal.model_validate(dict(row)) if row else None

    def get_by_account(self, account: str) -> Optional[UserInternal]:
        cursor = self.conn.execute("SELECT * FROM users WHERE account = ?", (account,))
        row = cursor.fetchone()
        return UserInternal.model_validate(dict(row)) if row else None
    
    def check_account(self, account: str) -> bool:
        cursor = self.conn.execute("SELECT 1 FROM users WHERE account = ? LIMIT 1", (account,))
        return cursor.fetchone() is not None

    def update_settings(self, uuid: str, trash_expire_days: Optional[int] = None, temp_expire_hours: Optional[int] = None, sliding_window_days: Optional[int] = None) -> int:
        fields = []
        params = []
        if trash_expire_days is not None:
            fields.append("trash_expire_days = ?")
            params.append(trash_expire_days)
        if temp_expire_hours is not None:
            fields.append("temp_expire_hours = ?")
            params.append(temp_expire_hours)
        if sliding_window_days is not None:
            fields.append("sliding_window_days = ?")
            params.append(sliding_window_days)
        
        if not fields: return 0
        
        query = f"UPDATE users SET {', '.join(fields)} WHERE uuid = ?"
        params.append(uuid)
        cursor = self.conn.execute(query, params)
        return cursor.rowcount

    def update_used_storage(self, uuid: str, delta_bytes: int) -> int:
        """更新已用空间量（支持正负）"""
        cursor = self.conn.execute(
            "UPDATE users SET used_storage = used_storage + ? WHERE uuid = ?",
            (delta_bytes, uuid)
        )
        return cursor.rowcount

    def get_trash_settings_for_all(self) -> list[sqlite3.Row]:
        """获取所有用户的回收站保留设置，用于定时清理"""
        cursor = self.conn.execute("SELECT uuid, trash_expire_days FROM users")
        return cursor.fetchall()

    def update_password_hash(self, uuid: str, password_hash: str) -> int:
        cursor = self.conn.execute("UPDATE users SET password_hash = ? WHERE uuid = ?", (password_hash, uuid))
        return cursor.rowcount

    def delete_user(self, uuid: str) -> int:
        cursor = self.conn.execute("DELETE FROM users WHERE uuid = ?", (uuid,))
        return cursor.rowcount

    def list_all(self) -> list[sqlite3.Row]:
        """管理员查看：拉取所有用户"""
        cursor = self.conn.execute("SELECT * FROM users ORDER BY created_at DESC")
        return cursor.fetchall()

    def update_quota(self, uuid: str, storage_quota: int) -> int:
        """管理员修改特定用户的存储配额"""
        cursor = self.conn.execute(
            "UPDATE users SET storage_quota = ? WHERE uuid = ?",
            (storage_quota, uuid)
        )
        return cursor.rowcount

    def update_status(self, uuid: str, is_active: bool) -> int:
        """管理员启用或禁用用户"""
        cursor = self.conn.execute(
            "UPDATE users SET is_active = ? WHERE uuid = ?",
            (1 if is_active else 0, uuid)
        )
        return cursor.rowcount
