from pathlib import Path
from typing import Optional

from core.config import settings
from core.logger import logger
from peewee import SqliteDatabase


class _Database:
    _instance: Optional[SqliteDatabase] = None
    _db_path: Path = settings.DB_NAME

    @classmethod
    def get_db(cls) -> SqliteDatabase:
        if cls._instance is None:
            cls._db_path.parent.mkdir(parents=True, exist_ok=True)
            cls._instance = SqliteDatabase(str(cls._db_path))
            logger.info(f"database initialized at {cls._db_path}")
        return cls._instance

    @classmethod
    def reset(cls, path: Path):
        cls._db_path = path
        cls._instance = None


def Database() -> SqliteDatabase:
    return _Database.get_db()
