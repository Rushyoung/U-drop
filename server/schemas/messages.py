from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FileInfoShort(BaseModel):
    """文件的物理元数据"""

    model_config = ConfigDict(from_attributes=True)
    full_hash: str = Field(
        ...,
        pattern="^[a-fA-F0-9]{64}$",
        description="文件的 Blake3 全量哈希值",
        json_schema_extra={"example": "4b1f8719..."},
    )
    file_size: int = Field(
        ..., description="文件大小 (Bytes)", json_schema_extra={"example": 266684}
    )
    mime_type: Optional[str] = Field(
        None, description="文件 MIME 类型", json_schema_extra={"example": "image/png"}
    )


class AttachmentResponse(BaseModel):
    """消息附件对象 (已持久化)"""

    model_config = ConfigDict(from_attributes=True)
    id: int = Field(..., description="附件关联记录 ID")
    file_hash: str = Field(..., pattern="^[a-fA-F0-9]{64}$", description="文件哈希")
    display_name: str = Field(..., description="显示名称")
    file_info: FileInfoShort = Field(..., description="物理详情")


class FileUploadIntent(BaseModel):
    """上传意图模型"""

    file_name: str = Field(..., description="待上传文件名")
    total_size: int = Field(..., ge=0, description="文件总字节数")
    sparse_hash: str = Field(..., pattern="^[a-fA-F0-9]{32}$", description="快速指纹")
    mime_type: Optional[str] = Field(None, description="MIME 类型")


class MessageCreateRequest(BaseModel):
    """创建消息请求 (支持多附件)"""

    content: Optional[str] = Field(
        None, description="文本内容", json_schema_extra={"example": "Hello!"}
    )
    type: Optional[Literal[0, 1]] = Field(
        None, description="指定展示类型 (0:纯文本, 1:混合/附件)"
    )
    files: List[FileUploadIntent] = Field(
        default_factory=list, description="要上传的文件列表"
    )
    tags: List[str] = Field(default_factory=list, description="标签列表")

    @model_validator(mode="after")
    def check_content_or_file(self):
        if not self.content and not self.files:
            raise ValueError("消息必须包含文本内容或至少一个上传文件")
        return self


class PendingUploadResponse(BaseModel):
    """正在上传中的附件信息 (内存态)"""

    upload_id: str = Field(..., description="上传任务 ID")
    file_name: str = Field(..., description="文件名")
    received_size: int = Field(..., description="已接收字节数")
    total_size: int = Field(..., description="总字节数")
    mime_type: Optional[str] = Field(None)
    status: str = Field("uploading", description="当前状态")


class BigFileReference(BaseModel):
    """大文件引用详情"""

    message_id: int = Field(..., description="引用该文件的消息 ID")
    attachment_id: int = Field(..., description="该次引用的附件关联 ID")
    display_name: str = Field(..., description="在该消息中的显示名称")


class BigFileResponse(BaseModel):
    """大文件猎手响应"""

    full_hash: str = Field(..., pattern="^[a-fA-F0-9]{64}$", description="文件全量哈希")
    file_size: int = Field(..., description="物理占用空间 (Bytes)")
    mime_type: Optional[str] = Field(None)
    refer_count: int = Field(..., description="全局物理引用计数")
    references: List[BigFileReference] = Field(
        default_factory=list, description="当前用户对该文件的详细引用清单"
    )


class MessageResponse(BaseModel):
    """完整消息响应模型 (解耦+幻影聚合)"""

    model_config = ConfigDict(from_attributes=True)
    id: int = Field(..., description="消息唯一 ID")
    type: int = Field(
        ..., description="展示类型 (0:纯文本, 1:混合)", json_schema_extra={"example": 1}
    )
    content: Optional[str] = Field(None, description="文本正文")
    timestamp: int = Field(..., description="创建时间戳")

    # 关联信息
    device_name: str = Field(..., description="发送设备")
    device_type: int = Field(..., description="设备类型")
    tags: List[str] = Field(default_factory=list, description="标签列表")

    # 附件展示
    attachments: List[AttachmentResponse] = Field(
        default_factory=list, description="已完成入库的附件"
    )
    pending_uploads: List[PendingUploadResponse] = Field(
        default_factory=list, description="正在上传中的附件幻影"
    )


class UploadTaskInfo(BaseModel):
    """创建任务后的简要回执"""

    upload_id: str
    file_name: str


class MessageCreateResponse(BaseModel):
    """消息创建结果"""

    status: str = Field(
        ...,
        description="'created' 或 'accepted'",
        json_schema_extra={"example": "accepted"},
    )
    message_id: int = Field(..., description="消息 ID")
    upload_tasks: List[UploadTaskInfo] = Field(
        default_factory=list, description="生成的上传任务清单"
    )
