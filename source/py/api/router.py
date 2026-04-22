from fastapi import APIRouter
from api.v1 import auth, files, messages

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["认证模块"])
router.include_router(messages.router, prefix="/messages", tags=["消息模块"])
router.include_router(files.router, prefix="/files", tags=["文件模块"])