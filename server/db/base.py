import sqlite3
from dataclasses import dataclass


@dataclass(slots=True)
class DatabaseSession:
    conn: sqlite3.Connection