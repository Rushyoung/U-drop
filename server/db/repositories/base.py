import sqlite3


class RepositoryBase:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn