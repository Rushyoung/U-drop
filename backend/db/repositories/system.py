import sqlite3
from db.repositories.base import RepositoryBase
from typing import Dict, Any

class SystemRepository(RepositoryBase):
    def get_setting(self, key: str, default: Any = None) -> Any:
        cursor = self.conn.execute("SELECT value FROM sys_settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row['value'] if row else default

    def set_setting(self, key: str, value: str):
        self.conn.execute(
            "INSERT OR REPLACE INTO sys_settings (key, value) VALUES (?, ?)",
            (key, value)
        )

    def get_all_settings(self) -> Dict[str, str]:
        cursor = self.conn.execute("SELECT key, value FROM sys_settings")
        return {row['key']: row['value'] for row in cursor.fetchall()}
