import secrets
from typing import Optional, Tuple

from server.core.exceptions import ForbiddenError, UdropException
from server.core.logger import logger
from server.database.models import Attachments, FileInfo, Messages, Shares
from server.database.services.file import FileService
from server.database.services.utils import AuthManager, get_time


class SharesError(UdropException):
    def __init__(self, Messages: str = "分享失效", code: int = 410) -> None:
        super().__init__(code, Messages)


class SharesService:
    def __init__(self, file_service: FileService) -> None:
        self.file_service = file_service

    def create_file_Shares(
        self,
        user_uuid: str,
        attachment_id: int,
        display_name: str,
        expire_in: Optional[int] = None,
        max_uses: int = 0,
        password: Optional[str] = None,
    ) -> Tuple[str, Optional[int]]:
        attach = Attachments.get_or_none(Attachments.id == attachment_id)
        if not attach:
            raise SharesError("附件不存在", 404)

        owns = bool(
            Attachments.select(Attachments.id)
            .join(Messages, on=(Attachments.message_id == Messages.id))
            .where(
                (Messages.sender_uuid == user_uuid) & (Attachments.id == attachment_id)
            )
            .limit(1)
            .exists()
        )
        if not owns:
            logger.warning(
                f"越权分享拦截 | 用户 {user_uuid[:8]} 试图分享不属于他的附件: {attachment_id}"
            )
            raise ForbiddenError("You don't have permission to Shares this Attachments")

        file_hash = attach.file_hash
        Shares_id = secrets.token_urlsafe(8)
        created_at = get_time()
        expire_time = (created_at + expire_in) if expire_in else None
        password_hash = AuthManager.get_password_hash(password) if password else None

        Shares.create(
            Shares_id=Shares_id,
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
            f"创建分享成功: ID={Shares_id} | 文件名={display_name} | 次数限制={max_uses}"
        )
        return Shares_id, expire_time

    def list_user_Sharess(self, user_uuid: str):
        return list(
            Shares.select(Shares, FileInfo.file_size)
            .join(
                FileInfo,
                on=(
                    (Shares.target_type == "file")
                    & (Shares.target_payload == FileInfo.full_hash)
                ),
                join_type="LEFT",
            )
            .where(Shares.creator_uuid == user_uuid)
            .order_by(Shares.created_at.desc())
        )

    def revoke_Shares(self, Shares_id: str, user_uuid: str):
        Shares = Shares.get_or_none(Shares.Shares_id == Shares_id)
        if not Shares:
            return False
        if Shares.creator_uuid != user_uuid:
            raise ForbiddenError("无权撤销他人的分享")
        Shares.delete().where(Shares.Shares_id == Shares_id).execute()
        logger.info(f"用户 {user_uuid[:8]} 撤销了分享: {Shares_id}")
        return True

    async def get_Sharesd_file(self, Shares_id: str, password: Optional[str] = None):
        Shares = Shares.get_or_none(Shares.Shares_id == Shares_id)
        if not Shares:
            logger.warning(f"分享访问失败: ID {Shares_id} 不存在")
            raise SharesError("分享链接不存在", 404)

        now = get_time()
        if Shares.expire_time and Shares.expire_time < now:
            logger.warning(f"分享已过期: ID {Shares_id}")
            raise SharesError("分享链接已过期")

        if Shares.password_hash:
            if not password or not AuthManager.verify_password_hash(
                password, Shares.password_hash
            ):
                logger.warning(f"提取码校验失败: ID {Shares_id}")
                raise SharesError("提取码错误", 403)

        affected = (
            Shares.update(use_count=Shares.use_count + 1)
            .where(
                (Shares.Shares_id == Shares_id)
                & ((Shares.max_uses == 0) | (Shares.use_count < Shares.max_uses))
            )
            .execute()
        )
        if affected == 0:
            logger.warning(f"分享链接无效或已达上限: ID {Shares_id}")
            raise SharesError("分享链接已失效或达到最大使用次数")
        logger.info(f"分享链接成功消费: ID {Shares_id} | 文件名={Shares.display_name}")

        file_hash = Shares.target_payload
        path, _ = await self.file_service.get_physical_path_and_name(file_hash)

        if not path or not path.exists():
            logger.error(f"源文件丢失: {file_hash}")
            raise SharesError("源文件已丢失", 404)

        return path, Shares.display_name
