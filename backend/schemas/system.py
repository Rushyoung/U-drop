from pydantic import BaseModel, Field
from typing import Optional

class SystemStatusResponse(BaseModel):
    """系统状态响应模型"""
    initialized: bool = Field(..., description="系统是否已完成初始管理员创建")
    version: str = Field(..., description="后端 API 版本号")
    allow_registration: bool = Field(..., description="是否允许开放注册")
    auth_rate_limit: int = Field(5, description="认证接口频率限制 (次/分钟)")
    default_token_expire: int = Field(86400, description="默认 Token 有效期 (秒)")

class SystemSetupRequest(BaseModel):
    """系统初始化请求模型"""
    account: str = Field(..., min_length=4, max_length=32, description="初始管理员账号")
    password: str = Field(..., min_length=8, description="管理员密码")
    allow_registration: bool = Field(True, description="是否在初始化后立即开放注册")
    auth_rate_limit: int = Field(5, ge=0, description="初始认证频率限制")
    default_token_expire: int = Field(86400, ge=60, description="初始默认 Token 有效期 (秒)")

class SystemSettingsUpdateRequest(BaseModel):
    """系统配置更新请求"""
    allow_registration: Optional[bool] = None
    auth_rate_limit: Optional[int] = Field(None, ge=0)
    default_token_expire: Optional[int] = Field(None, ge=60)

class FactoryResetRequest(BaseModel):
    """高危：工厂重置请求"""
    admin_password: str = Field(..., description="管理员密码（二次验证）")

class UserManageResponse(BaseModel):
    """管理员视角的用户信息"""
    uuid: str
    account: str
    role: str
    is_active: bool
    used_storage: int
    storage_quota: int
    created_at: int

class UserQuotaUpdateRequest(BaseModel):
    """用户配额更新请求"""
    storage_quota: int = Field(..., ge=0, description="新的存储配额 (Bytes)")

class UserStatusUpdateRequest(BaseModel):
    """用户启用/禁用请求"""
    is_active: bool = Field(..., description="是否启用用户")
