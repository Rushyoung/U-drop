import asyncio
import os
import time
import uuid
import weakref
from typing import List, Optional

import aiofiles
from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from server.core.config import settings
from server.core.exceptions import (
    ForbiddenError,
    HashMismatch,
    InternalError,
    TaskNotFound,
)
from server.core.logger import logger
from server.core.native_wrapper import native_core
from server.core.uploads_manager import UploadTask, uploads_manager
from server.core.websocket_manager import ws_manager
from server.database.models import Attachment, Message
from server.database.services.auth import AuthService
from server.database.services.file import FileService
from server.database.services.message import MessageService
from server.dependencies import (
    get_auth_service,
    get_current_session,
    get_file_service,
    get_message_service,
)
from server.schemas.base import COMMON_ERRORS, ResponseSchema
from server.schemas.messages import BigFileResponse

router = APIRouter(tags=["Phase 3: 极速文件流与配额管理"])

# 用户级并发锁：防止并发上传绕过配额检查
# 使用 WeakValueDictionary 确保当锁不再被任何协程持有时，自动从内存中释放
_USER_UPLOAD_LOCKS = weakref.WeakValueDictionary()
_LOCK_MANAGER_GUARD = asyncio.Lock()


async def get_user_lock(user_uuid: str) -> asyncio.Lock:
    """获取或创建用户专属的上传锁"""
    async with _LOCK_MANAGER_GUARD:
        lock = _USER_UPLOAD_LOCKS.get(user_uuid)
        if lock is None:
            lock = asyncio.Lock()
            _USER_UPLOAD_LOCKS[user_uuid] = lock
        return lock


async def _check_message_valid(message_id: int, message_service: MessageService):
    msg = Message.get_or_none(Message.id == message_id)
    if not msg or msg.deleted_at is not None:
        raise TaskNotFound("归属消息已进入回收站或不存在，无法继续上传")


async def _check_quota(user_uuid: str, total_size: int, auth_service: AuthService):
    """配额预检：确保用户空间足够"""
    user = auth_service.get_user_by_uuid(user_uuid)
    return user.used_storage + total_size <= user.storage_quota


async def _bind_file_to_message(
    task: UploadTask,
    file_hash: str,
    message_service: MessageService,
    auth_service: AuthService,
):
    """内部辅助：绑定附件并同步配额，最后发送 WS 信号 (真实 CAS 计费)"""
    message_service.bind_file_to_message(
        task.user_uuid, task.message_id, file_hash, task.file_name
    )
    await ws_manager.broadcast_to_user(
        task.user_uuid,
        {
            "type": "MSG_NEW",
            "data": {"message_id": task.message_id, "file_hash": file_hash},
        },
    )


@router.post(
    "/upload/init", response_model=ResponseSchema[dict], summary="初始化极速分片上传"
)
async def init_upload(
    message_id: int,
    file_name: str,
    total_size: int,
    sparse_hash: str,
    mime_type: Optional[str] = None,
    session=Depends(get_current_session),
    auth_service: AuthService = Depends(get_auth_service),
    message_service: MessageService = Depends(get_message_service),
):
    """
    第一步：创建上传任务。
    包含配额预检和消息合法性校验。
    """
    await _check_message_valid(message_id, message_service)

    user_lock = await get_user_lock(session["user_uuid"])
    async with user_lock:
        if not await _check_quota(session["user_uuid"], total_size, auth_service):
            raise ForbiddenError("存储空间不足")

        upload_id = str(uuid.uuid4())
        temp_dir = settings.STORAGE_ROOT / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / f"{upload_id}.tmp"
        uploads_manager.add_task(
            UploadTask(
                upload_id=upload_id,
                user_uuid=session["user_uuid"],
                message_id=message_id,
                file_name=file_name,
                total_size=total_size,
                sparse_hash=sparse_hash,
                mime_type=mime_type,
                temp_path=str(temp_path),
                created_at=int(time.time()),
            )
        )

    return ResponseSchema.ok(data={"upload_id": upload_id})


@router.patch(
    "/upload/{upload_id}",
    response_model=ResponseSchema[dict],
    summary="流式分片上传",
    responses={
        **COMMON_ERRORS,
        403: {"description": "存储空间不足或数据流超出声明大小"},
        404: {"description": "上传任务不存在或归属消息已删除"},
    },
    description="支持哈希劫持。若请求头包含 X-Full-Hash 且命中秒传，将立即终止上传并转为已完成附件。",
)
async def upload_file_chunked(
    request: Request,
    upload_id: str,
    x_full_hash: Optional[str] = Header(
        None,
        pattern="^[a-fA-F0-9]{64}$",
        description="可选：文件的全量哈希，用于秒传劫持",
    ),
    session=Depends(get_current_session),
    file_service: FileService = Depends(get_file_service),
    message_service: MessageService = Depends(get_message_service),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    第二步：流式分片传输。支持断点续传。
    """
    task = uploads_manager.get_task(upload_id)
    if not task or task.user_uuid != session["user_uuid"]:
        raise TaskNotFound()

    await _check_message_valid(task.message_id, message_service)

    # 秒传劫持判断
    if x_full_hash:
        existing_file = file_service.get_file_by_hash(x_full_hash)
        if existing_file:
            # 命中秒传：直接绑定，删除可能已产生的临时文件碎片
            user_lock = await get_user_lock(session["user_uuid"])
            async with user_lock:
                await _bind_file_to_message(
                    task, x_full_hash, message_service, auth_service
                )
                uploads_manager.remove_task(upload_id)
                if os.path.exists(task.temp_path):
                    os.remove(task.temp_path)
            logger.success(
                f"🚀 [秒传劫持] 命中: {x_full_hash[:16]}... | 消息: {task.message_id}"
            )
            return ResponseSchema.ok(
                data={"status": "deduplicated", "file_hash": x_full_hash}
            )

    try:
        async with aiofiles.open(task.temp_path, mode="ab") as f:
            curr = task.received_size
            chunk_count = 0
            async for chunk in request.stream():
                # 安全边界：检查是否溢出
                if curr + len(chunk) > task.total_size:
                    logger.error(
                        f"上传溢出拦截: 任务 {upload_id} 超出声明大小 {task.total_size}"
                    )
                    raise ForbiddenError("数据流超出任务声明大小，拒绝接收")

                await f.write(chunk)
                curr += len(chunk)
                chunk_count += 1

            uploads_manager.update_progress(upload_id, curr)

            # 若已传输完毕，可提示客户端调用 commit 或自动处理
            return ResponseSchema.ok(
                data={"received_size": curr, "total_size": task.total_size}
            )
    except Exception as e:
        if isinstance(e, ForbiddenError):
            raise e
        logger.error(f"分片写入异常: {e}")
        raise InternalError()


@router.post(
    "/upload/{upload_id}/commit",
    response_model=ResponseSchema[dict],
    summary="提交上传确认",
    responses={
        **COMMON_ERRORS,
        400: {"description": "哈希一致性校验失败 (HashMismatch)"},
    },
    description="上传完成后调用。后端会执行最终哈希校验并正式移动文件到 CAS 存储区。",
)
async def commit_upload(
    upload_id: str,
    x_full_hash: str = Header(
        ..., pattern="^[a-fA-F0-9]{64}$", description="文件的 Blake3 全量哈希"
    ),
    session=Depends(get_current_session),
    file_service: FileService = Depends(get_file_service),
    message_service: MessageService = Depends(get_message_service),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    第三步：提交确认。
    执行全量哈希校验，物理落盘，持久化附件关系。
    """
    task = uploads_manager.get_task(upload_id)
    if not task or task.user_uuid != session["user_uuid"]:
        raise ForbiddenError()

    # 耗时操作：全量哈希计算，使用线程池执行以防阻塞事件循环
    server_hash = await run_in_threadpool(native_core.get_full_blake3, task.temp_path)
    if server_hash != x_full_hash:
        logger.warning(
            f"哈希一致性失败! Client={x_full_hash[:10]}, Server={server_hash[:10]}"
        )
        uploads_manager.remove_task(upload_id)
        raise HashMismatch()

    user_lock = await get_user_lock(session["user_uuid"])
    async with user_lock:
        if not file_service.get_file_by_hash(server_hash):
            logger.info(
                f"新文件物理落盘: {server_hash[:16]}... | 原名: {task.file_name}"
            )
            await file_service.finalize_upload(
                task.temp_path,
                server_hash,
                task.sparse_hash,
                task.mime_type or "application/octet-stream",
            )

        # 核心修改：使用 message_service 统一处理 CAS 计费逻辑
        await _bind_file_to_message(task, server_hash, message_service, auth_service)
        uploads_manager.remove_task(upload_id)

    logger.success(f"附件处理完成: {task.file_name} -> 消息 {task.message_id}")
    return ResponseSchema.ok(data={"file_hash": server_hash})


@router.get(
    "/large",
    response_model=ResponseSchema[List[BigFileResponse]],
    summary="大文件猎手",
    responses=COMMON_ERRORS,
    description="列出当前用户占用的物理文件。每个文件会包含详细的引用清单（显示名称、消息ID），方便用户精细化清理存储配额。",
)
async def list_large_files(
    limit: int = Query(20, description="返回前多少个大文件"),
    session=Depends(get_current_session),
    message_service: MessageService = Depends(get_message_service),
):
    results = message_service.list_large_files(session["user_uuid"], limit=limit)
    return ResponseSchema.ok(data=results)


@router.delete(
    "/messages/{message_id}/attachments/{attachment_id}",
    response_model=ResponseSchema[None],
    summary="剥离附件引用",
    responses=COMMON_ERRORS,
    description="从特定消息中移除该附件记录。这是精细化释放配额的核心接口：若这是用户对该物理文件的最后一次引用，则返还配额并核减全局计数。若剥离后消息为空，将自动清理消息。",
)
async def detach_attachment(
    message_id: int,
    attachment_id: int,
    session=Depends(get_current_session),
    message_service: MessageService = Depends(get_message_service),
):
    """安全剥离特定引用并处理配额返还"""
    # 同样建议增加用户锁
    user_lock = await get_user_lock(session["user_uuid"])
    async with user_lock:
        success = message_service.detach_attachment_safe(
            session["user_uuid"], message_id, attachment_id
        )

    if not success:
        raise TaskNotFound("附件或引用关系不存在")
    return ResponseSchema.ok(message="Attachment detached and quota processed.")


@router.get(
    "/attachments/{attachment_id}/download",
    summary="附件下载",
    responses=COMMON_ERRORS,
    description="基于逻辑 ID 下载附件。后端会严格验证该附件是否属于当前登录用户，校验通过后解析物理哈希并流式返回文件。",
)
async def download_attachment(
    attachment_id: int,
    session=Depends(get_current_session),
    file_service: FileService = Depends(get_file_service),
    message_service: MessageService = Depends(get_message_service),
):
    """逻辑 ID 寻址下载：包含所有权校验"""
    # 1. 获取附件详情
    attach = Attachment.get_or_none(Attachment.id == attachment_id)
    if not attach:
        raise TaskNotFound("附件不存在")

    msg = Message.get_or_none(Message.id == attach.message_id)
    if not msg or msg.sender_uuid != session["user_uuid"]:
        logger.warning(
            f"越权下载拦截 | 用户 {session['user_uuid'][:8]} 试图下载附件 {attachment_id}"
        )
        raise ForbiddenError("You don't have access to this attachment")

    full_hash = attach.file_hash
    path, _ = await file_service.get_physical_path_and_name(full_hash)
    if not path or not path.exists():
        raise TaskNotFound("物理文件已丢失")

    logger.info(
        f"用户 {session['user_uuid'][:8]} 下载附件: {attach.display_name} (Hash: {full_hash[:8]}...)"
    )
    return FileResponse(
        path=path,
        filename=attach.display_name,
        media_type="application/octet-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.get(
    "/attachments/{attachment_id}/thumbnail",
    summary="获取附件缩略图",
    responses=COMMON_ERRORS,
    description="基于逻辑 ID 获取缩略图。同样具备严格的所有权校验。",
)
async def get_attachment_thumbnail(
    attachment_id: int,
    session=Depends(get_current_session),
    file_service: FileService = Depends(get_file_service),
    message_service: MessageService = Depends(get_message_service),
):
    """逻辑 ID 寻址缩略图：包含所有权校验"""
    # 1. 鉴权与获取哈希
    attach = Attachment.get_or_none(Attachment.id == attachment_id)
    if not attach:
        raise TaskNotFound("附件不存在")

    msg = Message.get_or_none(Message.id == attach.message_id)
    if not msg or msg.sender_uuid != session["user_uuid"]:
        raise ForbiddenError("Access denied")

    full_hash = attach.file_hash

    file_info = file_service.get_file_by_hash(full_hash)
    if not file_info:
        raise TaskNotFound()

    mime = file_info.mime_type or ""
    if not mime.startswith("image/"):
        raise ForbiddenError("Thumbnail not supported for non-image files")

    if file_info.file_size > 50 * 1024 * 1024:
        raise ForbiddenError("Original image too large for thumbnail generation")

    path = await file_service.get_or_create_thumbnail(full_hash)
    if not path or not os.path.exists(path):
        raise TaskNotFound()
    return FileResponse(path, media_type="image/jpeg")
