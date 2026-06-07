from fastapi import APIRouter, Depends, HTTPException
from schemas.base import ResponseSchema, COMMON_ERRORS
from schemas.system import SystemStatusResponse, SystemSetupRequest
from db.services.system_service import SystemService
from dependencies import get_system_service
from core.logger import logger

router = APIRouter(tags=["System: 系统状态与初始化向导"])

@router.get("/status", 
    response_model=ResponseSchema[SystemStatusResponse],
    summary="系统状态探测",
    description="供前端在启动时探测系统是否已初始化，以及当前的公开配置（如是否开放注册）。")
async def get_system_status(system_service: SystemService = Depends(get_system_service)):
    status = system_service.get_status()
    return ResponseSchema.ok(data=status)

@router.post("/setup", 
    response_model=ResponseSchema[None],
    summary="系统初始化向导",
    responses={403: {"description": "系统已初始化，拒绝二次调用"}},
    description="仅在系统未初始化时允许调用。用于创建首个超级管理员。一旦管理员存在，该接口将永久返回 403。")
async def initialize_system(req: SystemSetupRequest, system_service: SystemService = Depends(get_system_service)):
    success = system_service.initialize_system(
        account=req.account,
        password=req.password,
        allow_registration=req.allow_registration,
        auth_rate_limit=req.auth_rate_limit,
        default_token_expire=req.default_token_expire
    )
    if not success:
        raise HTTPException(status_code=403, detail="System already initialized")
    return ResponseSchema.ok(message="System initialized successfully.")
