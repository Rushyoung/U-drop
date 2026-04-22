from fastapi import APIRouter, Depends, HTTPException, Request, Header
import os
import aiofiles

from dependencies import get_file_service, get_message_service
from db.services.file_service import FileService
from db.services.message_service import MessageService
from core.uploads_manager import uploads_manager
from core.native_wrapper import native_core
from schemas.base import ResponseSchema

router = APIRouter()

@router.patch("/upload/{upload_id}", response_model=ResponseSchema[dict])
async def upload_file_chunked(
    request: Request,
    upload_id: str,
    x_full_hash: str = Header(None),
    file_service: FileService = Depends(get_file_service),
    message_service: MessageService = Depends(get_message_service)
):
    """
    流式文件接收与实时劫持。
    """
    task = uploads_manager.get_task(upload_id)
    if not task:
        raise HTTPException(status_code=404, detail="Upload task not found")

    # 1. 【核心拦截】检查客户端实时传来的 Full Hash
    if x_full_hash:
        existing_file = file_service.get_file_by_hash(x_full_hash)
        if existing_file:
            # 命中秒传，立即中断
            message_service.update_message_file(task.message_id, x_full_hash)
            uploads_manager.remove_task(upload_id)
            if os.path.exists(task.temp_path):
                os.remove(task.temp_path)
            
            return ResponseSchema.success(
                data={"status": "deduplicated", "file_hash": x_full_hash},
                message="Deduplication hit, upload interrupted."
            )

    # 2. 正常流式写入
    try:
        async with aiofiles.open(task.temp_path, mode='ab') as f:
            current_received = task.received_size
            async for chunk in request.stream():
                await f.write(chunk)
                current_received += len(chunk)
            
            uploads_manager.update_progress(upload_id, current_received)
            
        return ResponseSchema.success(
            data={"status": "uploading", "received_size": current_received}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload stream error: {str(e)}")


@router.post("/upload/{upload_id}/commit", response_model=ResponseSchema[dict])
async def commit_upload(
    upload_id: str,
    x_full_hash: str = Header(...), # Commit 阶段强制要求客户端提供它声明的哈希
    file_service: FileService = Depends(get_file_service),
    message_service: MessageService = Depends(get_message_service)
):
    """
    完成上传校验：
    1. 服务端重新计算哈希。
    2. 校验服务端哈希 vs 客户端提供的 Header 哈希。
    3. 不一致则报错。
    4. 一致则转存并更新消息。
    """
    task = uploads_manager.get_task(upload_id)
    if not task:
        raise HTTPException(status_code=404, detail="Upload task not found")

    if not os.path.exists(task.temp_path):
        raise HTTPException(status_code=500, detail="Temporary file missing")

    # 1. 服务端计算全量哈希 (Blake3)
    server_hash = native_core.get_full_blake3(task.temp_path)
    
    # 2. 【严谨校验】哈希不一致即报错
    if server_hash != x_full_hash:
        # 清理现场，防止脏数据残留
        uploads_manager.remove_task(upload_id)
        if os.path.exists(task.temp_path):
            os.remove(task.temp_path)
        raise HTTPException(
            status_code=400, 
            detail=f"Hash mismatch! Client: {x_full_hash}, Server: {server_hash}"
        )

    # 3. 检查库中是否已存在（双重检查）
    existing_file = file_service.get_file_by_hash(server_hash)
    if existing_file:
        message_service.update_message_file(task.message_id, server_hash)
        uploads_manager.remove_task(upload_id)
        os.remove(task.temp_path)
        return ResponseSchema.success(data={"file_hash": server_hash}, message="Upload completed via deduplication.")

    # 4. 正式转存
    await file_service.finalize_upload(
        temp_path=task.temp_path,
        file_name=task.file_name,
        full_hash=server_hash,
        mime_type=task.mime_type
    )

    # 5. 更新消息关联
    message_service.update_message_file(task.message_id, server_hash)

    # 6. 清理内存任务
    uploads_manager.remove_task(upload_id)

    return ResponseSchema.success(data={"file_hash": server_hash}, message="File uploaded and verified successfully.")
