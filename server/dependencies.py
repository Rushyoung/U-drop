import time

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from server.core.exceptions import TokenExpired
from server.core.logger import logger
from server.database.services.auth import AuthService
from server.database.services.file import FileService
from server.database.services.message import MessageService
from server.database.services.share import ShareService
from server.database.services.system import SystemService

security = HTTPBearer(auto_error=False)


def get_auth_service() -> AuthService:
    return AuthService()


async def get_current_session(
    request: Request,
    auth: HTTPAuthorizationCredentials = Security(security),
    auth_service: AuthService = Depends(get_auth_service),
):
    token = None

    if auth:
        token = auth.credentials

    if not token:
        if request.url.path == "/api/v1/ws" or request.url.path.startswith(
            "/api/v1/share/"
        ):
            token = request.query_params.get("token")

    if not token:
        logger.warning(
            f"鉴权失败: 缺少凭证或不允许通过 Query 传参 | 路径: {request.url.path}"
        )
        raise HTTPException(
            status_code=401,
            detail="Authentication credentials missing or not allowed in query",
        )

    now = int(time.time())

    try:
        session_info = auth_service.is_active_user(token, now, expire_enable=True)
        return session_info
    except TokenExpired:
        logger.warning(
            f"鉴权失败: Token 已过期或非法 -> {token[:10] if token else 'None'}... | 路径: {request.url.path}"
        )
        raise HTTPException(status_code=401, detail="Token expired or invalid")
    except Exception as e:
        logger.warning(f"鉴权失败: 异常错误 {str(e)} | 路径: {request.url.path}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


def get_file_service() -> FileService:
    return FileService()


def get_message_service() -> MessageService:
    return MessageService()


def get_share_service(
    file_service: FileService = Depends(get_file_service),
) -> ShareService:
    return ShareService(file_service)


def get_system_service() -> SystemService:
    return SystemService()


async def get_current_admin(
    session=Depends(get_current_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    user = auth_service.get_user_by_uuid(session["user_uuid"])
    if not user or user.role != "admin":
        logger.warning(f"越权尝试: 用户 {session['user_uuid'][:8]} 试图访问管理接口")
        from core.exceptions import ForbiddenError

        raise ForbiddenError("管理员权限不足")
    return user
