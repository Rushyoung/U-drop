import sqlite3
from fastapi import Depends
from db.connection import open_connection
from db.repositories.users import UserRepository
from db.repositories.devices import DeviceRepository
from db.services.auth_service import AuthService
from db.repositories.sessions import SessionRepository

def get_db():
    conn = open_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_auth_service(conn:sqlite3.Connection = Depends(get_db))->AuthService:
    user_repo = UserRepository(conn)
    device_repo = DeviceRepository(conn)
    sessions = SessionRepository(conn)
    return AuthService(user_repo, device_repo, sessions)
