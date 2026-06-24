import os
import time

from server.core.config import settings
from server.core.logger import logger
from server.core.uploads_manager import uploads_manager
from server.database.models import Attachments, FileInfo, Messages, Users
from server.database.services.auth import AuthService
from server.database.services.file import FileService
from server.tasks.register import register


@register("garbage_collection", interval=3600)
async def garbage_collection():
    AuthService.clean_expired_sessions()

    total_logic_cleaned = 0
    for user in Users.select(Users.uuid, Users.trash_expire_days):
        user_uuid = user.uuid
        expire_days = user.trash_expire_days
        cutoff = time.time() - (expire_days * 86400)

        expired_msgs = list(
            Messages.select(Messages.id, Messages.id.alias("mid")).where(
                (Messages.sender_uuid == user_uuid)
                & (Messages.deleted_at.is_null(False))
                & (Messages.deleted_at < cutoff)
            )
        )
        for msg_row in expired_msgs:
            mid = msg_row.id
            attachs = list(
                Attachments.select(Attachments, FileInfo.file_size)
                .join(FileInfo, on=(Attachments.file_hash == FileInfo.full_hash))
                .where(Attachments.message_id == mid)
            )
            total_size_freed = sum(a.file_size for a in attachs if a.file_size)
            Attachments.delete().where(Attachments.message_id == mid).execute()
            Messages.delete().where(Messages.id == mid).execute()
            if total_size_freed > 0:
                Users.update(used_storage=Users.used_storage - total_size_freed).where(
                    Users.uuid == user_uuid
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
