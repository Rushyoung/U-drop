from pydantic import BaseModel
from typing import Optional, List

class MessageCreateRequest(BaseModel):
    """创建消息请求"""
    content: Optional[str] = None
    file_name: Optional[str] = None
    sparse_hash: Optional[str] = None
    total_size: Optional[int] = 0
    tags: Optional[List[str]] = []

class MessageResponse(BaseModel):
    """消息返回模型"""
    id: int
    sender_uuid: str
    device_id: str
    type: int
    content: Optional[str]
    file_hash: Optional[str]
    timestamp: int
    is_deleted: int

    class Config:
        from_attributes = True

class MessageCreateResponse(BaseModel):
    """消息创建后的即时反馈"""
    status: str  # "created" 或 "accepted"
    message_id: int
    upload_id: Optional[str] = None
