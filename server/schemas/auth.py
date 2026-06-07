from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    account: str = Field(..., description="登录账号")
    uuid: str = Field(..., description="用户唯一标识 (内部 ID)")


class UserPublic(UserBase):
    role: str = Field("user", description="用户角色: admin 或 user")
    is_active: bool = Field(True, description="用户状态: 启用或禁用")
    created_at: int = Field(..., description="注册时间戳")
    trash_expire_days: int = Field(30, description="回收站自动清理天数")
    storage_quota: int = Field(5368709120, description="总存储配额 (Bytes)")
    used_storage: int = Field(0, description="已用存储空间 (Bytes)")
    sync_seq: int = Field(0, description="当前同步序列号 (用于端侧对齐)")
    temp_expire_hours: int = Field(24, description="临时 Session 有效小时数")
    sliding_window_days: int = Field(30, description="长效 Session 续期天数")


class UserInternal(UserPublic):
    password_hash: str


class UserSettingsUpdate(BaseModel):
    """用户设置更新请求"""

    trash_expire_days: Optional[int] = Field(
        None, ge=1, le=365, description="回收站保留天数 (1-365)"
    )
    temp_expire_hours: Optional[int] = Field(
        None, ge=1, le=24, description="临时 Session 寿命 (1-24小时)"
    )
    sliding_window_days: Optional[int] = Field(
        None, ge=1, le=365, description="滑动窗口续期天数 (1-365)"
    )


class DeviceUpdateRequest(BaseModel):
    """设备信息更新请求"""

    device_name: str = Field(
        ..., min_length=1, max_length=50, description="新设备显示名称"
    )


class LoginRequest(BaseModel):
    account: str
    password: str
    device_id: str
    device_type: int
    device_name: Optional[str] = None
    expire_time: Optional[int] = 0  # 旧版兼容
    expire_in: Optional[int] = Field(None, description="自定义有效期(秒)")
    single_use: bool = Field(False, description="是否一次性 Token，用完即焚")
    remember_me: bool = Field(False, description="是否开启长效登录 (滑动窗口续期)")


class LoginData(BaseModel):
    """登录成功后的返回数据"""

    bearer: Optional[str] = Field(None, description="鉴权 Token")


class LogoutRequest(BaseModel):
    bearer: str


class PasswordChangeRequest(BaseModel):
    """修改密码请求"""

    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=8, description="新密码")


class DeviceResponse(BaseModel):
    """设备列表响应项"""

    model_config = ConfigDict(from_attributes=True)
    device_id: str = Field(..., description="设备唯一 ID")
    device_type: int = Field(..., description="设备类型 (0:Web, 1:Android, 2:PC)")
    device_name: Optional[str] = Field(None, description="设备显示名称")
    last_seen: int = Field(..., description="最后在线时间戳")
