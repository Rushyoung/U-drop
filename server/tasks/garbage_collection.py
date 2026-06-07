import os
import time

from server.core.config import settings
from server.core.logger import logger
from server.core.uploads_manager import uploads_manager
from server.database.models import Attachment, FileInfo, Message, User
from server.database.services.auth import AuthService
from server.database.services.file import FileService
from server.tasks.register import register


@register("garbage_collection", interval=3600)
async def garbage_collection():
    AuthService.clean_expired_sessions()

    total_logic_cleaned = 0
    for user in User.select(User.uuid, User.trash_expire_days):
        user_uuid = user.uuid
        expire_days = user.trash_expire_days
        cutoff = time.time() - (expire_days * 86400)

        expired_msgs = list(
            Message.select(Message.id, Message.id.alias("mid")).where(
                (Message.sender_uuid == user_uuid)
                & (Message.deleted_at.is_null(False))
                & (Message.deleted_at < cutoff)
            )
        )
        for msg_row in expired_msgs:
            mid = msg_row.id
            attachs = list(
                Attachment.select(Attachment, FileInfo.file_size)
                .join(FileInfo, on=(Attachment.file_hash == FileInfo.full_hash))
                .where(Attachment.message_id == mid)
            )
            total_size_freed = sum(a.file_size for a in attachs if a.file_size)
            Attachment.delete().where(Attachment.message_id == mid).execute()
            Message.delete().where(Message.id == mid).execute()
            if total_size_freed > 0:
                User.update(used_storage=User.used_storage - total_size_freed).where(
                    User.uuid == user_uuid
                ).execute()
            total_logic_cleaned += 1

    total_phys_cleaned = await FileService().cleanup_orphan_files()

    temp_dir = settings.STORAGE_ROOT / "temp"
    total_tmp_cleaned = 0

    uploads_manager.cleanup_old_tasks(86400)

    if temp_dir.exists():
        now = time.time()
        for tmp_file in temp_dir.iterdir():
            if tmp_file.is_file() and (now - tmp_file.stat().st_mtime > 86400):
                upload_id = tmp_file.name.replace(".tmp", "")
                if not uploads_manager.get_task(upload_id):
                    try:
                        os.remove(tmp_file)
                        total_tmp_cleaned += 1
                    except Exception:
                        pass

    if total_logic_cleaned > 0 or total_phys_cleaned > 0 or total_tmp_cleaned > 0:
        logger.success(
            f"GC 清理完成：逻辑删除 {total_logic_cleaned} 条，物理回收 {total_phys_cleaned} 个，清理碎片 {total_tmp_cleaned} 个。"
        )
