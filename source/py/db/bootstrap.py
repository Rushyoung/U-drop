from db.connection import open_connection
from core.config import settings


def initialize_database(conn=None) -> None:
    if conn is None:
        conn = open_connection()
        should_close = True
    else:
        should_close = False

    try:
        with open(settings.DB_INIT, "r", encoding="utf-8") as file_handle:
            sqlscript = file_handle.read()
        conn.executescript(sqlscript)
        conn.commit()
    finally:
        if should_close:
            conn.close()