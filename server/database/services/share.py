import secrets
from typing import Optional, Tuple

from server.core.exceptions import ForbiddenError, UdropException
from server.core.logger import logger
from server.database.models import Attachment, Message, Share
from server.database.services.file import FileService
from server.database.services.utils import AuthManager, get_time


class ShareError(UdropException):
    def __init__(self, message: str = "分享失效", code: int = 410) -> None:
        super().__init__(code, message)


class ShareService:
    def __init__(self, file_service: FileService) -> None:
        self.file_service = file_service

    def create_file_share(
        self,
        user_uuid: str,
        attachment_id: int,
        display_name: str,
        expire_in: Optional[int] = None,
        max_uses: int = 0,
        password: Optional[str] = None,
    ) -> Tuple[str, Optional[int]]:
        attach = Attachment.get_or_none(Attachment.id == attachment_id)
        if not attach:
            raise ShareError("附件不存在", 404)

        owns = bool(
            Attachment.select(Attachment.id)
            .join(Message, on=(Attachment.message_id == Message.id))
            .where(
                (Message.sender_uuid == user_uuid) & (Attachment.id == attachment_id)
            )
            .limit(1)
            .exists()
        )
        if not owns:
            logger.warning(
                f"越权分享拦截 | 用户 {user_uuid[:8]} 试图分享不属于他的附件: {attachment_id}"
            )
            raise ForbiddenError("You don't have permission to share this attachment")

        file_hash = attach.file_hash
        share_id = secrets.token_urlsafe(8)
        created_at = get_time()
        expire_time = (created_at + expire_in) if expire_in else None
        password_hash = AuthManager.get_password_hash(password) if password else None

        Share.create(
            share_id=share_id,
            creator_uuid=user_uuid,
            target_type="file",
            target_payload=file_hash,
            display_name=display_name,
            expire_time=expire_time,
            max_uses=max_uses,
            password_hash=password_hash,
            created_at=created_at,
        )
        logger.info(
            f"创建分享成功: ID={share_id} | 文件名={display_name} | 次数限制={max_uses}"
        )
        return share_id, expire_time

    def list_user_shares(self, user_uuid: str):
        return list(
            Share.select()
            .where(Share.creator_uuid == user_uuid)
            .order_by(Share.created_at.desc())
        )

    def revoke_share(self, share_id: str, user_uuid: str):
        share = Share.get_or_none(Share.share_id == share_id)
        if not share:
            return False
        if share.creator_uuid != user_uuid:
            raise ForbiddenError("无权撤销他人的分享")
        Share.delete().where(Share.share_id == share_id).execute()
        logger.info(f"用户 {user_uuid[:8]} 撤销了分享: {share_id}")
        return True

    async def get_shared_file(self, share_id: str, password: Optional[str] = None):
        share = Share.get_or_none(Share.share_id == share_id)
        if not share:
            logger.warning(f"分享访问失败: ID {share_id} 不存在")
            raise ShareError("分享链接不存在", 404)

        now = get_time()
        if share.expire_time and share.expire_time < now:
            logger.warning(f"分享已过期: ID {share_id}")
            raise ShareError("分享链接已过期")

        if share.password_hash:
            if not password or not AuthManager.verify_password_hash(
                password, share.password_hash
            ):
                logger.warning(f"提取码校验失败: ID {share_id}")
                raise ShareError("提取码错误", 403)

        if share.max_uses > 0 and share.use_count >= share.max_uses:
            logger.warning(f"分享链接无效或已达上限: ID {share_id}")
            raise ShareError("分享链接已失效或达到最大使用次数")

        (
            Share.update(use_count=Share.use_count + 1)
            .where(Share.share_id == share_id)
            .execute()
        )
        logger.info(f"分享链接成功消费: ID {share_id} | 文件名={share.display_name}")

        file_hash = share.target_payload
        path, _ = await self.file_service.get_physical_path_and_name(file_hash)

        if not path or not path.exists():
            logger.error(f"源文件丢失: {file_hash}")
            raise ShareError("源文件已丢失", 404)

        return path, share.display_name
