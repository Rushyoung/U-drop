import time
import os
from typing import Dict, Optional, List
from pydantic import BaseModel
from core.logger import logger

class UploadTask(BaseModel):
    """内存中的上传任务模型"""
    upload_id: str
    user_uuid: str
    message_id: int
    file_name: str
    total_size: int
    sparse_hash: str
    received_size: int = 0
    temp_path: str
    created_at: int
    mime_type: Optional[str] = "application/octet-stream"

class UploadsManager:
    """管理内存中的上传任务"""
    def __init__(self):
        self._tasks: Dict[str, UploadTask] = {}

    def add_task(self, task: UploadTask):
        self._tasks[task.upload_id] = task

    def get_task(self, upload_id: str) -> Optional[UploadTask]:
        return self._tasks.get(upload_id)

    def update_progress(self, upload_id: str, received_size: int):
        if upload_id in self._tasks:
            self._tasks[upload_id].received_size = received_size

    def remove_task(self, upload_id: str):
        """物理清理临时文件并移除任务"""
        if upload_id in self._tasks:
            task = self._tasks[upload_id]
            if os.path.exists(task.temp_path):
                try:
                    os.remove(task.temp_path)
                except Exception as e:
                    logger.error(f"Failed to cleanup temp file: {e}")
            del self._tasks[upload_id]
            logger.info(f"Upload task removed: {upload_id}")

    def list_user_tasks(self, user_uuid: str) -> List[UploadTask]:
        return [t for t in self._tasks.values() if t.user_uuid == user_uuid]

    def list_by_message_id(self, message_id: int) -> List[UploadTask]:
        """筛选属于特定消息的上传任务"""
        return [t for t in self._tasks.values() if t.message_id == message_id]

    def cleanup_old_tasks(self, max_age_seconds: int = 86400):
        """清理超过指定时间的过期任务 (默认 24 小时)"""
        now = int(time.time())
        expired_ids = [uid for uid, task in self._tasks.items() if now - task.created_at > max_age_seconds]
        for uid in expired_ids:
            self.remove_task(uid)
        if expired_ids:
            logger.info(f"UploadsManager | 清理了 {len(expired_ids)} 个过期上传任务")

uploads_manager = UploadsManager()
