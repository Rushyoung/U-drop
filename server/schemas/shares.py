from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ShareCreateRequest(BaseModel):
    """创建分享链接请求"""

    attachment_id: int = Field(..., description="要分享的附件逻辑 ID")
    display_name: str = Field(
        ...,
        description="下载时固化的文件名",
        json_schema_extra={"example": "我的考研资料.pdf"},
    )
    expire_in: Optional[int] = Field(
        None, description="有效期(秒)，NULL 为永久", json_schema_extra={"example": 3600}
    )
    max_uses: int = Field(
        1,
        ge=0,
        description="最大使用次数，0 为无限制",
        json_schema_extra={"example": 1},
    )
    password: Optional[str] = Field(
        None, description="访问密码 (可选)", json_schema_extra={"example": "1234"}
    )


class ShareCreateResponse(BaseModel):
    """分享链接创建响应"""

    share_id: str = Field(..., description="分享 ID")
    share_url: str = Field(..., description="完整的分享链接")
    expire_time: Optional[int] = Field(None, description="到期时间戳")


class ShareItemResponse(BaseModel):
    """分享条目信息"""

    model_config = ConfigDict(from_attributes=True)
    share_id: str
    target_type: str
    target_payload: str
    display_name: Optional[str] = Field(None, description="分享时固化的显示名称")
    expire_time: Optional[int]
    max_uses: int
    use_count: int
    created_at: int

    # --- 关联资源详情 (由后端 JOIN 查出) ---
    file_size: Optional[int] = Field(None, description="原始文件大小")
