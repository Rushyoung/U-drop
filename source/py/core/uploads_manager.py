import time
from typing import Dict, Optional
from pydantic import BaseModel

class UploadTask(BaseModel):
    """内存中的上传任务模型"""
    upload_id: str
    user_uuid: str
    message_id: int
    file_name: str
    total_size: int
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
        if upload_id in self._tasks:
            del self._tasks[upload_id]

    def list_user_tasks(self, user_uuid: str) -> list[UploadTask]:
        return [t for t in self._tasks.values() if t.user_uuid == user_uuid]

# 单例
uploads_manager = UploadsManager()
