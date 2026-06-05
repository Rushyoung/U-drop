from fastapi import APIRouter
from api.v1 import auth, files, messages, shares, websocket, system, manage

router = APIRouter()

router.include_router(auth.router, prefix="/auth")
router.include_router(messages.router, prefix="/messages")
router.include_router(files.router, prefix="/files")
router.include_router(shares.router, prefix="/share")
router.include_router(system.router, prefix="/system")
router.include_router(manage.router, prefix="/manage")
router.include_router(websocket.router)
