from fastapi import APIRouter

from server.api.v1 import auth, files, manage, messages, shares, system, websocket

router = APIRouter()

router.include_router(auth.router, prefix="/auth")
router.include_router(messages.router, prefix="/messages")
router.include_router(files.router, prefix="/files")
router.include_router(shares.router, prefix="/share")
router.include_router(system.router, prefix="/system")
router.include_router(manage.router, prefix="/manage")
router.include_router(websocket.router)
