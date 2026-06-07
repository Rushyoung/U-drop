from fastapi import APIRouter, Depends, HTTPException
from typing import List
import sqlite3

from schemas.base import ResponseSchema, COMMON_ERRORS
from schemas.system import (
    SystemSettingsUpdateRequest, UserManageResponse, FactoryResetRequest, 
    UserQuotaUpdateRequest, UserStatusUpdateRequest
)
from schemas.auth import UserPublic
from db.services.system_service import SystemService
from db.services.auth_service import AuthService
from db.services.utils import AuthManager
from dependencies import get_system_service, get_auth_service, get_current_admin, get_db
from core.logger import logger

router = APIRouter(tags=["Manage: 后台管理接口"], dependencies=[Depends(get_current_admin)])

@router.get("/settings", response_model=ResponseSchema[dict], summary="获取系统全局配置")
async def get_manage_settings(system_service: SystemService = Depends(get_system_service)):
    return ResponseSchema.ok(data=system_service.get_status())

@router.put("/settings", response_model=ResponseSchema[None], summary="修改系统全局配置")
async def update_manage_settings(req: SystemSettingsUpdateRequest, system_service: SystemService = Depends(get_system_service)):
    system_service.update_settings(
        allow_registration=req.allow_registration,
        auth_rate_limit=req.auth_rate_limit,
        default_token_expire=req.default_token_expire
    )
    return ResponseSchema.ok(message="Settings updated.")

@router.get("/users", response_model=ResponseSchema[List[UserManageResponse]], summary="用户列表管理")
async def list_users(auth_service: AuthService = Depends(get_auth_service)):
    rows = auth_service.users.list_all()
    # 转换为响应模型
    users = [
        UserManageResponse(
            uuid=r['uuid'],
            account=r['account'],
            role=r['role'],
            is_active=bool(r['is_active']),
            used_storage=r['used_storage'],
            storage_quota=r['storage_quota'],
            created_at=r['created_at']
        ) for r in rows
    ]
    return ResponseSchema.ok(data=users)

@router.put("/users/{user_uuid}/quota", response_model=ResponseSchema[None], summary="修改用户存储配额")
async def update_user_quota(
    user_uuid: str, 
    req: UserQuotaUpdateRequest,
    current_admin = Depends(get_current_admin),
    auth_service: AuthService = Depends(get_auth_service)
):
    """管理员手动调整用户的最大存储限制 (Bytes)"""
    auth_service.admin_update_quota(current_admin.uuid, user_uuid, req.storage_quota)
    return ResponseSchema.ok(message="User quota updated.")

@router.put("/users/{user_uuid}/status", response_model=ResponseSchema[None], summary="启用/禁用用户")
async def update_user_status(
    user_uuid: str,
    req: UserStatusUpdateRequest,
    current_admin = Depends(get_current_admin),
    auth_service: AuthService = Depends(get_auth_service)
):
    """管理员禁用用户后，该用户将无法登录且当前会话立即失效"""
    auth_service.admin_update_status(current_admin.uuid, user_uuid, req.is_active)
    return ResponseSchema.ok(message=f"User {'enabled' if req.is_active else 'disabled'}.")

@router.delete("/users/{user_uuid}", response_model=ResponseSchema[None], summary="彻底销毁用户 (安全级联)")
async def delete_user_permanently(
    user_uuid: str,
    current_admin = Depends(get_current_admin),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    极高危：物理销毁用户及其所有物理资源引用。
    会自动扣减关联文件的引用计数，并踢出该用户所有在线设备。
    """
    auth_service.admin_hard_delete_user(current_admin.uuid, user_uuid)
    return ResponseSchema.ok(message="User and associated resources destroyed.")

@router.post("/factory_reset", 
    response_model=ResponseSchema[None], 
    summary="工厂重置 (极其危险)",
    responses={403: {"description": "管理员密码验证失败"}},
    description="验证管理员密码后，清空系统所有业务数据。")
async def factory_reset(
    req: FactoryResetRequest, 
    current_admin = Depends(get_current_admin),
    system_service: SystemService = Depends(get_system_service),
    conn: sqlite3.Connection = Depends(get_db)
):
    """验证管理员密码后，清空系统所有业务数据"""
    # 1. 验证密码
    if not AuthManager.verify_password_hash(req.admin_password, current_admin.password_hash):
        logger.warning(f"工厂重置失败 | 管理员 {current_admin.account} 密码验证失败")
        raise HTTPException(status_code=403, detail="Invalid admin password")
    
    # 2. 执行重置
    system_service.factory_reset(conn)
    return ResponseSchema.ok(message="Factory reset complete. System is now uninitialized.")
