from fastapi import APIRouter, Depends, HTTPException
from typing import List
from db.services.auth_service import AuthService
from db.services.system_service import SystemService
from dependencies import get_auth_service, get_current_session, get_system_service
from schemas.auth import (
    LoginRequest, LoginData, LogoutRequest, UserPublic, 
    UserSettingsUpdate, DeviceUpdateRequest, PasswordChangeRequest,
    DeviceResponse
)
from schemas.base import ResponseSchema, COMMON_ERRORS
from core.websocket_manager import ws_manager
from core.system_guard import feature_gate

router = APIRouter(tags=["Phase 1: 账号与设备管理"])

from core.exceptions import AccountRepeat, LoginError, ForbiddenError
...
@router.post("/register", 
    response_model=ResponseSchema[LoginData], 
    summary="用户注册", 
    responses={**COMMON_ERRORS, 400: {"description": "账号名不符合要求或已被占用"}},
    description="注册新账号并自动关联当前设备，返回初始化 Token。受系统 allow_registration 配置控制。")
@feature_gate("allow_registration")
def register(
    req: LoginRequest, 
    auth: AuthService = Depends(get_auth_service)
):
    try:
        auth.register_user(req.account, req.password)
    except AccountRepeat:
        # 安全加固：模糊化账号存在性响应，防止枚举
        logger.warning(f"注册拦截 | 账号冲突枚举尝试: {req.account}")
        raise HTTPException(status_code=400, detail="Invalid account or already taken")
        
    return ResponseSchema.ok(data=auth.login(**req.model_dump()))

@router.post("/login", 
    response_model=ResponseSchema[LoginData], 
    summary="用户登录", 
    responses={401: {"description": "账号或密码错误"}},
    description="支持跨端登录。可通过 expire_in 自定义有效期，或开启 single_use 实现用后即焚。")
def login(req: LoginRequest, auth: AuthService = Depends(get_auth_service)):
    return ResponseSchema.ok(data=auth.login(**req.model_dump()))

@router.post("/logout", response_model=ResponseSchema[None], summary="注销登录")
def logout(req: LogoutRequest, auth: AuthService = Depends(get_auth_service)):
    auth.logout(req.bearer)
    return ResponseSchema.ok(message="Successfully logged out.")

@router.get("/me", 
    response_model=ResponseSchema[UserPublic], 
    summary="获取个人信息", 
    responses=COMMON_ERRORS,
    description="返回当前用户的存储配额、已用空间、同步序列号及回收站设置。")
async def get_me(
    session = Depends(get_current_session),
    auth_service: AuthService = Depends(get_auth_service)
):
    """返回当前用户的配额、已用空间及内存中的最新 Sync Seq"""
    user_row = auth_service.get_user_by_uuid(session["user_uuid"])
    user_dict = dict(user_row)
    user_dict["sync_seq"] = ws_manager.get_current_seq(session["user_uuid"])
    
    return ResponseSchema.ok(data=UserPublic.model_validate(user_dict))

@router.put("/settings", response_model=ResponseSchema[None], summary="更新偏好设置", description="支持修改回收站清理天数、临时 Session 寿命及滑动窗口续期天数。")
async def update_settings(
    req: UserSettingsUpdate, 
    session = Depends(get_current_session), 
    auth_service: AuthService = Depends(get_auth_service)
):
    """更新用户的偏好设置与会话有效期策略"""
    auth_service.update_user_settings(
        session["user_uuid"], 
        trash_expire_days=req.trash_expire_days,
        temp_expire_hours=req.temp_expire_hours,
        sliding_window_days=req.sliding_window_days
    )
    return ResponseSchema.ok(message="Settings updated.")

@router.put("/device", response_model=ResponseSchema[None], summary="更新当前设备名称", description="修改当前登录会话所关联的设备显示名称。会通过 WebSocket 实时通知所有在线端同步缓存。")
async def update_current_device(
    req: DeviceUpdateRequest, 
    session = Depends(get_current_session), 
    auth_service: AuthService = Depends(get_auth_service)
):
    """更新当前登录设备的显示名称并通知各端"""
    auth_service.update_device_name(session["device_id"], req.device_name)
    
    # WebSocket 广播：设备信息变更，触发 Seq 增长以强制同步
    await ws_manager.broadcast_to_user(session["user_uuid"], {
        "type": "DEVICE_UPDATE",
        "data": {
            "device_id": session["device_id"],
            "device_name": req.device_name
        }
    }, bump_seq=True)
    
    return ResponseSchema.ok(message="Device name updated and sync broadcast sent.")

@router.put("/password", response_model=ResponseSchema[None], summary="修改登录密码")
async def change_password(
    req: PasswordChangeRequest,
    session = Depends(get_current_session),
    auth_service: AuthService = Depends(get_auth_service)
):
    """用户自行修改密码"""
    auth_service.change_password(session["user_uuid"], req.old_password, req.new_password)
    return ResponseSchema.ok(message="Password changed.")

@router.get("/devices", response_model=ResponseSchema[List[DeviceResponse]], summary="获取设备列表")
async def list_devices(
    session = Depends(get_current_session),
    auth_service: AuthService = Depends(get_auth_service)
):
    """列出当前账号下所有已登录设备"""
    devices = auth_service.list_user_devices(session["user_uuid"])
    return ResponseSchema.ok(data=devices)

@router.delete("/devices/{device_id}", response_model=ResponseSchema[None], summary="注销特定设备")
async def revoke_device(
    device_id: str,
    session = Depends(get_current_session),
    auth_service: AuthService = Depends(get_auth_service)
):
    """强制注销某个设备，使其所有会话失效并踢出"""
    success = auth_service.revoke_device(session["user_uuid"], device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Device not found or access denied")
    return ResponseSchema.ok(message="Device revoked successfully.")
