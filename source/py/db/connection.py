import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from core.config import settings



def open_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def connection_scope() -> Iterator[sqlite3.Connection]:
    conn = open_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()