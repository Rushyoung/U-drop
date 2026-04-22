import sqlite3
from fastapi import Depends
from db.connection import open_connection
from db.repositories.users import UserRepository
from db.repositories.devices import DeviceRepository
from db.services.auth_service import AuthService
from db.repositories.sessions import SessionRepository
from db.repositories.file_info import FileInfoRepository
from db.repositories.messages import MessageRepository
from db.repositories.hashtags import HashtagRepository
from db.repositories.message_tags import MessageTagRepository
from db.repositories.upload_tasks import UploadTaskRepository
from db.services.file_service import FileService
from db.services.message_service import MessageService

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


def get_file_service(conn: sqlite3.Connection = Depends(get_db)) -> FileService:
    file_info_repo = FileInfoRepository(conn)
    return FileService(file_info_repo)


def get_upload_task_repo(conn: sqlite3.Connection = Depends(get_db)) -> UploadTaskRepository:
    return UploadTaskRepository(conn)


def get_message_service(conn: sqlite3.Connection = Depends(get_db)) -> MessageService:
    messages = MessageRepository(conn)
    file_info = FileInfoRepository(conn)
    hashtags = HashtagRepository(conn)
    message_tags = MessageTagRepository(conn)
    return MessageService(messages, file_info, hashtags, message_tags)
