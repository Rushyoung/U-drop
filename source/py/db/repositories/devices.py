import sqlite3

from db.repositories.base import RepositoryBase


class DeviceRepository(RepositoryBase):
    def create_device(
        self,
        device_id: str,
        user_uuid: str,
        device_type: int,
        device_name: str | None,
        last_seen: int | None,
    ) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO devices (device_id, user_uuid, device_type, device_name, last_seen) VALUES (?, ?, ?, ?, ?)",
            (device_id, user_uuid, device_type, device_name, last_seen),
        )

    def get_by_device_id(self, device_id: str) -> sqlite3.Row | None:
        if not device_id:
            raise ValueError('device id is invalid!')
        cursor = self.conn.execute(
            "SELECT * FROM devices WHERE device_id = ?",
            (device_id.strip(),),
        )
        return cursor.fetchone()

    def list_by_user_uuid(self, user_uuid: str) -> list[sqlite3.Row]:
        cursor = self.conn.execute("SELECT * FROM devices WHERE user_uuid = ?", (user_uuid,))
        return cursor.fetchall()

    def touch_last_seen(self, device_id: str, last_seen: int) -> int:
        cursor = self.conn.execute(
            "UPDATE devices SET last_seen = ? WHERE device_id = ?",
            (last_seen, device_id),
        )
        return cursor.rowcount

    def delete_device(self, device_id: str) -> int:
        cursor = self.conn.execute("DELETE FROM devices WHERE device_id = ?", (device_id,))
        return cursor.rowcount