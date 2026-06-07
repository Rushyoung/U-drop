import os
import time

from core.config import settings
from core.logger import logger
from core.uploads_manager import uploads_manager
from db.connection import db
from db.repositories.attachments import AttachmentRepository
from db.repositories.file_info import FileInfoRepository
from db.repositories.messages import MessageRepository
from db.repositories.users import UserRepository
from db.services.auth_service import AuthService

from server.tasks.register import register


@register("garbage_collection", interval=3600)
def garbage_collection():
    with db.atomic():
        user_repo = UserRepository()
        msg_repo = MessageRepository()
        attach_repo = AttachmentRepository()
        file_info_repo = FileInfoRepository()

        AuthService.clean_expired_sessions()

        total_logic_cleaned = 0
        user_settings = user_repo.get_trash_settings_for_all()
        for user in user_settings:
            user_uuid = user.uuid
            expire_days = user.trash_expire_days
            expired_msgs = msg_repo.list_expired_for_user(user_uuid, expire_days)
            for msg_row in expired_msgs:
                mid = msg_row.id
                attachs = attach_repo.list_by_message_id(mid)
                total_size_freed = sum([a["file_size"] for a in attachs])
                attach_repo.delete_by_message_id(mid)
                msg_repo.hard_delete_message(mid)
                user_repo.update_used_storage(user_uuid, -total_size_freed)
                total_logic_cleaned += 1

        total_phys_cleaned = 0
        orphans = file_info_repo.list_orphans()
        for row in orphans:
            full_hash = row["full_hash"]
            storage_path = row["storage_path"]
            if storage_path.startswith("local://"):
                rel_path = storage_path.replace("local://", "")
                abs_path = settings.STORAGE_ROOT / rel_path
                if abs_path.exists():
                    try:
                        os.remove(abs_path)
                    except Exception:
                        pass
            thumb_path = settings.THUMBNAIL_ROOT / f"{full_hash}.jpg"
            if thumb_path.exists():
                try:
                    os.remove(thumb_path)
                except Exception:
                    pass
            file_info_repo.delete_file_info(full_hash)
            total_phys_cleaned += 1

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
