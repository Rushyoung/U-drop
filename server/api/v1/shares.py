from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse

from server.core.logger import logger
from server.database.services.share import ShareService
from server.dependencies import get_current_session, get_share_service
from server.schemas.base import ResponseSchema
from server.schemas.shares import (
    ShareCreateRequest,
    ShareCreateResponse,
    ShareItemResponse,
)

router = APIRouter(tags=["Phase 4: 分享中心"])


@router.post(
    "/file",
    response_model=ResponseSchema[ShareCreateResponse],
    summary="为附件生成分享链接",
)
async def create_file_share_link(
    req: ShareCreateRequest,
    request: Request,
    session=Depends(get_current_session),
    share_service: ShareService = Depends(get_share_service),
):
    """
    为指定的附件 ID 生成分享票据。
    后端会验证该附件是否属于当前用户。
    """
    # display_name 现在优先从请求中获取，如果没有则可能由 service 层处理
    display_name = req.display_name if req.display_name else "shared_file"

    share_id, expire_time = share_service.create_file_share(
        user_uuid=session["user_uuid"],
        attachment_id=req.attachment_id,
        display_name=display_name,
        expire_in=req.expire_in,
        max_uses=req.max_uses,
        password=req.password,
    )

    base_url = str(request.base_url).rstrip("/")
    share_url = f"{base_url}/api/v1/share/{share_id}"

    return ResponseSchema.ok(
        data=ShareCreateResponse(
            share_id=share_id, share_url=share_url, expire_time=expire_time
        )
    )


@router.get(
    "/list",
    response_model=ResponseSchema[List[ShareItemResponse]],
    summary="列出我创建的分享",
)
async def list_my_shares(
    session=Depends(get_current_session),
    share_service: ShareService = Depends(get_share_service),
):
    rows = share_service.list_user_shares(session["user_uuid"])
    return ResponseSchema.ok(
        data=[ShareItemResponse.model_validate(dict(row)) for row in rows]
    )


@router.delete(
    "/{share_id}", response_model=ResponseSchema[None], summary="撤销分享链接"
)
async def revoke_share_link(
    share_id: str,
    session=Depends(get_current_session),
    share_service: ShareService = Depends(get_share_service),
):
    share_service.revoke_share(share_id, session["user_uuid"])
    return ResponseSchema.ok(message="分享已撤销")


@router.get("/{share_id}", summary="解析分享链接并下载")
async def download_shared_file(
    share_id: str,
    pwd: Optional[str] = None,
    share_service: ShareService = Depends(get_share_service),
):
    path, original_name = await share_service.get_shared_file(share_id, password=pwd)

    # 增加审计日志
    logger.info(f"分享链接被访问: ID {share_id} -> 文件 {original_name}")

    return FileResponse(
        path=path,
        filename=original_name,
        media_type="application/octet-stream",
        headers={"Cache-Control": "no-cache"},
    )
