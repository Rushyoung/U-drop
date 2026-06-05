from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
import time
import uuid
import os

from dependencies import get_message_service, get_file_service, get_current_session
from db.services.message_service import MessageService
from db.services.file_service import FileService
from core.uploads_manager import uploads_manager, UploadTask
from core.websocket_manager import ws_manager
from core.config import settings
from schemas.base import ResponseSchema
from schemas.messages import MessageCreateRequest, MessageCreateResponse, MessageResponse, UploadTaskInfo
from core.exceptions import ForbiddenError, TaskNotFound
from core.logger import logger

router = APIRouter(tags=["Phase 2: 消息与时间线实时同步"])

@router.post("", 
    response_model=ResponseSchema[MessageCreateResponse],
    summary="发送消息",
    description="核心入口。支持纯文本及多附件。如果是附件消息，会立即分配 upload_id 并进入内存待上传状态。")
async def create_message(
    msg: MessageCreateRequest,
    session = Depends(get_current_session),
    message_service: MessageService = Depends(get_message_service)
):
    user_uuid = session["user_uuid"]
    device_id = session["device_id"]
    timestamp = int(time.time())
    
    m_type = msg.type
    if m_type is None:
        m_type = 1 if msg.files else 0

    message_id = message_service.create_message(
        sender_uuid=user_uuid,
        device_id=device_id,
        message_type=m_type,
        content=msg.content,
        timestamp=timestamp,
        tag_names=msg.tags
    )
    logger.info(f"消息已创建: ID={message_id} | 来源={user_uuid[:8]} | 附件数={len(msg.files)}")

    await ws_manager.broadcast_to_user(user_uuid, {
        "type": "MSG_NEW",
        "data": {"message_id": message_id}
    })

    upload_infos = []
    if msg.files:
        for file_intent in msg.files:
            upload_id = str(uuid.uuid4())
            temp_dir = settings.STORAGE_ROOT / "temp"
            temp_dir.mkdir(parents=True, exist_ok=True)
            temp_path = temp_dir / f"{upload_id}.tmp"

            task = UploadTask(
                upload_id=upload_id,
                user_uuid=user_uuid,
                message_id=message_id,
                file_name=file_intent.file_name,
                total_size=file_intent.total_size,
                sparse_hash=file_intent.sparse_hash,
                mime_type=file_intent.mime_type,
                temp_path=str(temp_path),
                created_at=timestamp
            )
            uploads_manager.add_task(task)
            upload_infos.append(UploadTaskInfo(upload_id=upload_id, file_name=file_intent.file_name))
            logger.debug(f"  └─ 待上传: {file_intent.file_name} ({file_intent.mime_type or 'unknown'}) | Size: {file_intent.total_size} | TaskID: {upload_id[:8]}...")

    return ResponseSchema.ok(
        data=MessageCreateResponse(status="accepted" if upload_infos else "created", message_id=message_id, upload_tasks=upload_infos),
        message="Message created."
    )

@router.get("", 
    response_model=ResponseSchema[List[MessageResponse]],
    summary="拉取消息列表",
    description="采用基于 Anchor 的自适应滑动窗口算法。mode=initial 时以 anchor_id 为中心向两端探测，确保上下文均衡加载。")
async def list_messages(
    mode: str = Query("initial", description="initial: 初始加载, before: 向旧消息翻页, after: 探测新消息"),
    anchor_id: Optional[int] = Query(None, description="锚点消息 ID"),
    limit: int = Query(50, ge=1, le=100),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    hashtag: Optional[str] = Query(None, description="标签搜索"),
    session = Depends(get_current_session),
    message_service: MessageService = Depends(get_message_service),
):
    results = message_service.list_timeline(user_uuid=session["user_uuid"], limit=limit, anchor_id=anchor_id, mode=mode, keyword=keyword, hashtag=hashtag)
    logger.info(f"Timeline | 用户 {session['user_uuid'][:8]} 拉取消息 | Mode: {mode} | Anchor: {anchor_id} | 结果: {len(results)} 条")
    return ResponseSchema.ok(data=results)

@router.get("/trash", response_model=ResponseSchema[List[MessageResponse]], summary="查看回收站")
async def get_trash(session = Depends(get_current_session), message_service: MessageService = Depends(get_message_service)):
    results = message_service.list_trash(session["user_uuid"])
    return ResponseSchema.ok(data=results)

@router.post("/{message_id}/restore", response_model=ResponseSchema[None], summary="恢复消息")
async def restore_message(message_id: int, session = Depends(get_current_session), message_service: MessageService = Depends(get_message_service)):
    message_service.restore_message(message_id, session["user_uuid"])
    await ws_manager.broadcast_to_user(session["user_uuid"], {"type": "MSG_NEW", "data": {"message_id": message_id}})
    return ResponseSchema.ok(message="Restored.")

@router.delete("/trash/empty", response_model=ResponseSchema[None], summary="清空回收站", description="彻底物理删除当前用户回收站内的所有消息及其附件，并全额释放存储配额。")
async def empty_trash(session = Depends(get_current_session), message_service: MessageService = Depends(get_message_service)):
    count = message_service.empty_user_trash(session["user_uuid"])
    return ResponseSchema.ok(message=f"Cleaned {count} items.")

@router.delete("/{message_id}", response_model=ResponseSchema[None], summary="删除消息 (进入回收站)")
async def delete_message(message_id: int, session = Depends(get_current_session), message_service: MessageService = Depends(get_message_service)):
    msg = message_service.messages.get_by_id(message_id)
    if not msg or msg['deleted_at'] is not None: raise TaskNotFound("消息不存在")
    if msg['sender_uuid'] != session["user_uuid"]: raise ForbiddenError()
    message_service.delete_message(message_id)
    await ws_manager.broadcast_to_user(session["user_uuid"], {"type": "MSG_DELETE", "data": {"message_id": message_id}})
    return ResponseSchema.ok(message="Moved to trash.")
