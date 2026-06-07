import sqlite3
import time
from fastapi import Depends, HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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
from db.repositories.shares import ShareRepository
from db.repositories.attachments import AttachmentRepository
from db.services.file_service import FileService
from db.services.message_service import MessageService
from db.services.share_service import ShareService
from core.exceptions import TokenExpired
from core.logger import logger

# 定义 Bearer Token 提取器
security = HTTPBearer(auto_error=False)

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

def get_auth_service(conn: sqlite3.Connection = Depends(get_db)) -> AuthService:
    user_repo = UserRepository(conn)
    device_repo = DeviceRepository(conn)
    sessions = SessionRepository(conn)
    return AuthService(user_repo, device_repo, sessions)

async def get_current_session(
    request: Request,
    auth: HTTPAuthorizationCredentials = Security(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> sqlite3.Row:
    """
    FastAPI 依赖项：鉴权并返回当前会话。
    支持从 Header (Bearer) 或 Query Parameter (?token=) 提取 Token。
    """
    token = None
    
    # 1. 优先尝试从 Header 提取
    if auth:
        token = auth.credentials
    
    # 2. 如果 Header 没有，尝试从 Query 参数提取 (仅限特定白名单路径)
    if not token:
        # 修复：改为前缀匹配，支持 /api/v1/share/{id} 等动态路径
        if request.url.path == "/api/v1/ws" or request.url.path.startswith("/api/v1/share/"):
             token = request.query_params.get("token")
        
    if not token:
        logger.warning(f"鉴权失败: 缺少凭证或不允许通过 Query 传参 | 路径: {request.url.path}")
        raise HTTPException(status_code=401, detail="Authentication credentials missing or not allowed in query")

    now = int(time.time())
    
    try:
        # 调用 is_active_user (支持一次性 Token 消费逻辑)
        session_info = auth_service.is_active_user(token, now, expire_enable=True)
        return session_info
    except TokenExpired:
        logger.warning(f"鉴权失败: Token 已过期或非法 -> {token[:10] if token else 'None'}... | 路径: {request.url.path}")
        raise HTTPException(status_code=401, detail="Token expired or invalid")
    except Exception as e:
        logger.warning(f"鉴权失败: 异常错误 {str(e)} | 路径: {request.url.path}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

def get_file_service(conn: sqlite3.Connection = Depends(get_db)) -> FileService:
    file_info_repo = FileInfoRepository(conn)
    return FileService(file_info_repo)

def get_upload_task_repo(conn: sqlite3.Connection = Depends(get_db)) -> UploadTaskRepository:
    return UploadTaskRepository(conn)

def get_message_service(conn: sqlite3.Connection = Depends(get_db)) -> MessageService:
    users = UserRepository(conn)
    messages = MessageRepository(conn)
    file_info = FileInfoRepository(conn)
    hashtags = HashtagRepository(conn)
    message_tags = MessageTagRepository(conn)
    attachments = AttachmentRepository(conn)
    return MessageService(messages, file_info, hashtags, message_tags, attachments, users)

from db.repositories.system import SystemRepository
from db.services.system_service import SystemService
from core.exceptions import ForbiddenError, TokenExpired
...
def get_share_service(conn: sqlite3.Connection = Depends(get_db)) -> ShareService:
    shares = ShareRepository(conn)
    file_service = get_file_service(conn)
    attachments = AttachmentRepository(conn)
    return ShareService(shares, file_service, attachments)

def get_system_service(conn: sqlite3.Connection = Depends(get_db)) -> SystemService:
    return SystemService(SystemRepository(conn), UserRepository(conn))

async def get_current_admin(session = Depends(get_current_session), auth_service: AuthService = Depends(get_auth_service)):
    """权限校验：仅允许角色为 admin 的用户通过"""
    user = auth_service.get_user_by_uuid(session["user_uuid"])
    if not user or user.role != 'admin':
        logger.warning(f"越权尝试: 用户 {session['user_uuid'][:8]} 试图访问管理接口")
        raise ForbiddenError("管理员权限不足")
    return user
