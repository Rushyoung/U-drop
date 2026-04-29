import time
import secrets
from typing import Optional, Tuple, List
from db.repositories.shares import ShareRepository
from db.repositories.attachments import AttachmentRepository
from db.services.file_service import FileService
from db.services.utils import AuthManager, get_time
from core.exceptions import UdropException, ForbiddenError
from core.logger import logger

class ShareError(UdropException):
    def __init__(self, message: str = "分享失效", code: int = 410) -> None:
        super().__init__(code, message)

class ShareService:
    def __init__(self, shares: ShareRepository, file_service: FileService, attachments: AttachmentRepository) -> None:
        self.shares = shares
        self.file_service = file_service
        self.attachments = attachments

    def create_file_share(
        self, 
        user_uuid: str, 
        attachment_id: int, 
        display_name: str,
        expire_in: Optional[int] = None, 
        max_uses: int = 0,
        password: Optional[str] = None
    ) -> Tuple[str, Optional[int]]:
        """创建一个文件分享链接，由逻辑 ID 寻址并固化名称"""
        # 1. 获取附件信息并验证所有权
        attach = self.attachments.get_attachment_by_id(attachment_id)
        if not attach:
            raise ShareError("附件不存在", 404)
        
        # 查所属消息验证归属 (需引入 MessageRepository 或通过 Repository 联查，此处直接联表校验)
        # 为简化，我们在 Repository 层面直接支持带用户校验的查询
        if not self.attachments.check_user_has_attachment(user_uuid, attachment_id):
            logger.warning(f"越权分享拦截 | 用户 {user_uuid[:8]} 试图分享不属于他的附件: {attachment_id}")
            raise ForbiddenError("You don't have permission to share this attachment")

        file_hash = attach['file_hash']
        share_id = secrets.token_urlsafe(8)
        created_at = get_time()
        expire_time = (created_at + expire_in) if expire_in else None
        password_hash = AuthManager.get_password_hash(password) if password else None

        self.shares.create_share(
            share_id=share_id,
            creator_uuid=user_uuid,
            target_type="file",
            target_payload=file_hash,
            display_name=display_name,
            expire_time=expire_time,
            max_uses=max_uses,
            password_hash=password_hash,
            created_at=created_at
        )
        logger.info(f"创建分享成功: ID={share_id} | 文件名={display_name} | 次数限制={max_uses}")
        return share_id, expire_time

    def list_user_shares(self, user_uuid: str):
        return self.shares.list_by_user(user_uuid)

    def revoke_share(self, share_id: str, user_uuid: str):
        share = self.shares.get_share(share_id)
        if not share: return False
        if share["creator_uuid"] != user_uuid:
            raise ForbiddenError("无权撤销他人的分享")
        self.shares.delete_share(share_id)
        logger.info(f"用户 {user_uuid[:8]} 撤销了分享: {share_id}")
        return True

    async def get_shared_file(self, share_id: str, password: Optional[str] = None):
        """解析分享链接，记录日志并消耗次数"""
        # 1. 获取分享记录
        share = self.shares.get_share(share_id)
        if not share:
            logger.warning(f"分享访问失败: ID {share_id} 不存在")
            raise ShareError("分享链接不存在", 404)

        now = get_time()
        if share["expire_time"] and share["expire_time"] < now:
            logger.warning(f"分享已过期: ID {share_id}")
            raise ShareError("分享链接已过期")

        # 2. 验证提取码
        if share["password_hash"]:
            if not password or not AuthManager.verify_password_hash(password, share["password_hash"]):
                logger.warning(f"提取码校验失败: ID {share_id}")
                raise ShareError("提取码错误", 403)

        # 3. 原子化消耗次数 (解决竞态条件)
        success = self.shares.consume_share_atomic(share_id)
        if not success:
            logger.warning(f"分享链接无效或已达上限: ID {share_id}")
            raise ShareError("分享链接已失效或达到最大使用次数")

        logger.info(f"分享链接成功消费: ID {share_id} | 文件名={share['display_name']}")

        file_hash = share["target_payload"]
        path, _ = await self.file_service.get_physical_path_and_name(file_hash)
        
        if not path or not path.exists():
            logger.error(f"源文件丢失: {file_hash}")
            raise ShareError("源文件已丢失", 404)

        return path, share["display_name"]
