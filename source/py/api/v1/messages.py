from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
import time
import uuid
import os

from dependencies import get_message_service, get_file_service
from db.services.message_service import MessageService
from db.services.file_service import FileService
from core.uploads_manager import uploads_manager, UploadTask
from core.config import settings
from schemas.base import ResponseSchema
from schemas.messages import MessageCreateRequest, MessageCreateResponse

router = APIRouter()

@router.post("", response_model=ResponseSchema[MessageCreateResponse])
async def create_message(
    msg: MessageCreateRequest,
    message_service: MessageService = Depends(get_message_service),
    file_service: FileService = Depends(get_file_service),
    # TODO: 接入真实 User 鉴权与设备识别
    user_uuid: str = "test-user-uuid",
    device_id: str = "test-device-id"
):
    """
    创建消息：
    1. 如果是纯文本，直接创建并返回 created。
    2. 如果带文件信息，先查稀疏哈希。
    3. 无论是否可能秒传，都先创建消息占位符和内存上传任务，返回 accepted。
    """
    timestamp = int(time.time())
    
    # 消息类型约定：0:文本, 1:图片, 2:文件 (对应 init.sql)
    # 这里简单判断，实际可根据 mime_type 细化
    m_type = 0
    if msg.file_name:
        m_type = 2 # 默认为文件

    # 1. 创建消息记录 (file_hash 初始为 None)
    message_id = message_service.create_message(
        sender_uuid=user_uuid,
        device_id=device_id,
        message_type=m_type,
        content=msg.content,
        file_hash=None,
        timestamp=timestamp,
        tag_names=msg.tags
    )

    # 2. 如果是文件消息，注册内存上传任务
    if m_type != 0:
        upload_id = str(uuid.uuid4())
        
        # 预备临时存储路径
        temp_dir = settings.STORAGE_ROOT / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / f"{upload_id}.tmp"

        task = UploadTask(
            upload_id=upload_id,
            user_uuid=user_uuid,
            message_id=message_id,
            file_name=msg.file_name,
            total_size=msg.total_size,
            temp_path=str(temp_path),
            created_at=timestamp
        )
        uploads_manager.add_task(task)

        return ResponseSchema.success(
            data=MessageCreateResponse(
                status="accepted",
                message_id=message_id,
                upload_id=upload_id
            ),
            message="Message accepted, please start uploading file."
        )

    return ResponseSchema.success(
        data=MessageCreateResponse(status="created", message_id=message_id),
        message="Message created successfully."
    )
