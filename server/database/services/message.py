import html
from typing import List, Optional

from peewee import fn

from server.core.exceptions import ForbiddenError
from server.core.logger import logger
from server.core.uploads_manager import uploads_manager
from server.database.models import (
    Attachment,
    FileInfo,
    Message,
    User,
)
from server.database.services.utils import get_time
from server.schemas.messages import (
    BigFileReference,
    BigFileResponse,
    MessageResponse,
    PendingUploadResponse,
)


class MessageService:
    def create_message(
        self,
        sender_uuid: str,
        device_id: str,
        message_type: int,
        content: Optional[str],
        timestamp: int,
        tag_names: Optional[List[str]] = None,
        file_hash: Optional[str] = None,
        file_name: Optional[str] = None,
    ) -> int:
        safe_content = html.escape(content) if content else None

        msg = Message.create(
            sender_uuid=sender_uuid,
            device_id=device_id,
            type=message_type,
            content=safe_content,
            timestamp=timestamp,
        )

        if file_hash:
            Attachment.create(
                message_id=msg.id,
                file_hash=file_hash,
                display_name=file_name or "未命名文件",
            )
            FileInfo.update(refer_count=FileInfo.refer_count + 1).where(
                FileInfo.full_hash == file_hash
            ).execute()

        if tag_names:
            pass

        return msg.id  # type: ignore

    def list_timeline(self, user_uuid: str, **kwargs) -> List[MessageResponse]:
        rows = self._list_messages(user_uuid, deleted=False, **kwargs)
        return self._aggregate_attachments(rows)

    def list_trash(self, user_uuid: str) -> List[MessageResponse]:
        rows = (
            Message.select()
            .where(
                (Message.sender_uuid == user_uuid) & (Message.deleted_at.is_null(False))
            )
            .order_by(Message.deleted_at.desc())
            .execute()
        )
        return self._aggregate_attachments(rows)

    def _list_messages(self, user_uuid: str, deleted: bool = False, **kwargs):
        query = (
            Message.select()
            .where(
                (Message.sender_uuid == user_uuid)
                & (
                    Message.deleted_at.is_null()
                    if not deleted
                    else Message.deleted_at.is_null(False)
                )
            )
            .order_by(Message.timestamp.desc())
        )
        limit = kwargs.get("limit")
        offset = kwargs.get("offset")
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        return query.execute()

    def _aggregate_attachments(self, rows) -> List[MessageResponse]:
        if not rows:
            return []
        message_ids = [r.id for r in rows]

        attach_rows = (
            Attachment.select(
                Attachment,
                FileInfo.file_size,
                FileInfo.mime_type,
                FileInfo.storage_path,
            )
            .join(FileInfo, on=(Attachment.file_hash == FileInfo.full_hash))
            .where(Attachment.message_id.in_(message_ids))
            .order_by(Attachment.message_id.desc(), Attachment.sort_order.asc())
            .execute()
        )

        attach_map: dict[int, list] = {}
        for ar in attach_rows:
            m_id = ar.message_id
            if m_id not in attach_map:
                attach_map[m_id] = []
            attach_map[m_id].append(ar)

        results = []
        for row in rows:
            msg_dict = dict(row)
            m_id = msg_dict["id"]
            msg_dict["attachments"] = []
            if m_id in attach_map:
                for ar in attach_map[m_id]:
                    msg_dict["attachments"].append(
                        {
                            "id": ar.id,
                            "file_hash": ar.file_hash,
                            "display_name": ar.display_name,
                            "file_info": {
                                "full_hash": ar.file_hash,
                                "file_size": ar.file_size,
                                "mime_type": ar.mime_type,
                            },
                        }
                    )

            pending_tasks = uploads_manager.list_by_message_id(m_id)
            msg_dict["pending_uploads"] = [
                PendingUploadResponse(
                    upload_id=t.upload_id,
                    file_name=t.file_name,
                    received_size=t.received_size,
                    total_size=t.total_size,
                    mime_type=t.mime_type,
                    status="uploading",
                )
                for t in pending_tasks
            ]
            msg_dict["tags"] = []
            results.append(MessageResponse.model_validate(msg_dict))
        return results

    def bind_file_to_message(
        self, user_uuid: str, message_id: int, file_hash: str, display_name: str
    ):
        is_paying = bool(
            Attachment.select(Attachment.id)
            .join(Message, on=(Attachment.message_id == Message.id))
            .where(
                (Message.sender_uuid == user_uuid) & (Attachment.file_hash == file_hash)
            )
            .limit(1)
            .exists()
        )

        Attachment.create(
            message_id=message_id, file_hash=file_hash, display_name=display_name
        )
        FileInfo.update(refer_count=FileInfo.refer_count + 1).where(
            FileInfo.full_hash == file_hash
        ).execute()

        if not is_paying:
            file_info = FileInfo.get_or_none(FileInfo.full_hash == file_hash)
            if file_info:
                User.update(used_storage=User.used_storage + file_info.file_size).where(
                    User.uuid == user_uuid
                ).execute()
                logger.info(
                    f"计费 | 用户 {user_uuid[:8]} 为新哈希支付配额: {file_info.file_size} Bytes"
                )
        else:
            logger.info(f"计费 | 用户 {user_uuid[:8]} 秒传复用已有引用，不重复扣费")

    def detach_attachment_safe(
        self, user_uuid: str, message_id: int, attachment_id: int
    ):
        msg_row = Message.get_or_none(Message.id == message_id)
        if not msg_row or msg_row.sender_uuid != user_uuid:
            logger.warning(
                f"越权告警 | 用户 {user_uuid[:8]} 试图剥离不属于他的消息附件: MessageID={message_id}"
            )
            return False

        attach = Attachment.get_or_none(Attachment.id == attachment_id)
        if not attach:
            return False

        file_hash = attach.file_hash
        file_info = FileInfo.get_or_none(FileInfo.full_hash == file_hash)
        file_size = file_info.file_size if file_info else 0

        FileInfo.update(refer_count=FileInfo.refer_count - 1).where(
            FileInfo.full_hash == file_hash
        ).execute()
        Attachment.delete().where(Attachment.id == attachment_id).execute()
        logger.info(f"清理 | 附件 {attachment_id} 已从消息 {message_id} 剥离")

        if not self._user_has_file(user_uuid, file_hash):
            User.update(used_storage=User.used_storage - file_size).where(
                User.uuid == user_uuid
            ).execute()
            logger.success(
                f"计费 | 用户 {user_uuid[:8]} 已彻底释放哈希引用，配额返还: {file_size} Bytes"
            )

        remaining = list(Attachment.select().where(Attachment.message_id == message_id))
        if not remaining and (not msg_row.content or not msg_row.content.strip()):
            Message.delete().where(Message.id == message_id).execute()
            logger.info(f"清理 | 消息 {message_id} 因内容为空已被自动清除")

        return True

    def _user_has_file(self, user_uuid: str, file_hash: str) -> bool:
        return bool(
            Attachment.select(Attachment.id)
            .join(Message, on=(Attachment.message_id == Message.id))
            .where(
                (Message.sender_uuid == user_uuid) & (Attachment.file_hash == file_hash)
            )
            .limit(1)
            .exists()
        )

    def _hard_delete_single(self, message_id: int, user_uuid: str):
        attachs = list(Attachment.select().where(Attachment.message_id == message_id))
        for a in attachs:
            self.detach_attachment_safe(user_uuid, message_id, a.id)

    def restore_message(self, message_id: int, user_uuid: str):
        msg = Message.get_or_none(Message.id == message_id)
        if not msg or msg.sender_uuid != user_uuid:
            raise ForbiddenError("消息不存在或无权恢复")
        return Message.update(deleted_at=None).where(Message.id == message_id).execute()

    def empty_user_trash(self, user_uuid: str) -> int:
        trash_ids = list(
            Message.select(Message.id).where(
                (Message.sender_uuid == user_uuid) & (Message.deleted_at.is_null(False))
            )
        )
        count = 0
        for m in trash_ids:
            self._hard_delete_single(m.id, user_uuid)
            count += 1
        return count

    def delete_message(self, message_id: int) -> bool:
        return (
            Message.update(deleted_at=get_time())
            .where(Message.id == message_id)
            .execute()
            > 0
        )

    def list_large_files(
        self, user_uuid: str, limit: int = 20
    ) -> List[BigFileResponse]:
        query = (
            FileInfo.select(
                FileInfo.full_hash,
                FileInfo.file_size,
                FileInfo.mime_type,
                FileInfo.refer_count,
                fn.GROUP_CONCAT(
                    Message.id.cast("text")
                    + ":"
                    + Attachment.id.cast("text")
                    + ":"
                    + Attachment.display_name,
                    "|",
                ).alias("ref_info"),
            )
            .join(Attachment, on=(FileInfo.full_hash == Attachment.file_hash))
            .join(Message, on=(Attachment.message_id == Message.id))
            .where((Message.sender_uuid == user_uuid) & (Message.deleted_at.is_null()))
            .group_by(FileInfo.full_hash)
            .order_by(FileInfo.file_size.desc())
            .limit(limit)
            .dicts()
            .execute()
        )

        results = []
        for r in query:
            refs = []
            if r["ref_info"]:
                for ref_str in r["ref_info"].split("|"):
                    parts = ref_str.split(":", 2)
                    if len(parts) == 3:
                        refs.append(
                            BigFileReference(
                                message_id=int(parts[0]),
                                attachment_id=int(parts[1]),
                                display_name=parts[2],
                            )
                        )
            results.append(
                BigFileResponse(
                    full_hash=r["full_hash"],
                    file_size=r["file_size"],
                    mime_type=r["mime_type"],
                    refer_count=r["refer_count"],
                    references=refs,
                )
            )
        return results
