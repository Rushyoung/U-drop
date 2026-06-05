from collections.abc import Generator
from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from db.bootstrap import initialize_database
from db.connection import open_connection


class Database:
    def __init__(self, conn) -> None:
        self.conn = conn


def get_service() -> Generator[Database, None, None]:
    conn = open_connection()
    initialize_database(conn)
    try:
        yield Database(conn)
    finally:
        conn.close()






    


