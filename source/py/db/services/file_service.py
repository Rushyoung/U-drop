import os
from pathlib import Path
from fastapi.concurrency import run_in_threadpool
from db.repositories.file_info import FileInfoRepository
from core.native_wrapper import native_core
from core.config import settings
import shutil

class FileService:
    def __init__(self, file_info: FileInfoRepository) -> None:
        self.file_info = file_info

    def get_file_by_hash(self, full_hash: str):
        """用于秒传检查"""
        return self.file_info.get_by_full_hash(full_hash)

    async def save_uploaded_file(self, file_content: bytes, file_name: str, full_hash: str, mime_type: str) -> str:
        """保存文件到磁盘并记录到数据库"""
        # 1. 确定存储路径 (按 hash 前两位分目录)
        sub_dir = full_hash[:2]
        save_dir = settings.STORAGE_ROOT / sub_dir
        save_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = save_dir / full_hash
        
        # 2. 写入物理文件 (同步操作建议跑在线程池)
        def _write():
            with open(file_path, "wb") as f:
                f.write(file_content)
        
        await run_in_threadpool(_write)
        
        # 3. 记录数据库
        self.file_info.upsert_file(
            full_hash=full_hash,
            sparse_hash=None, # [TODO] 补充快速哈希逻辑
            file_name=file_name,
            file_size=len(file_content),
            mime_type=mime_type,
            storage_path=str(file_path.relative_to(settings.PROJECT_ROOT)),
            thumbnail_url=None
        )
        
        return str(file_path)

    async def trigger_thumbnail_process(self, full_hash: str, file_path: str):
        """异步触发缩略图生成"""
        # 只对图片生成缩略图 (简单判断)
        # [TODO] 增加更严谨的 MIME 校验
        thumb_name = f"{full_hash}_thumb.jpg"
        thumb_path = settings.THUMBNAIL_ROOT / thumb_name
        
        # 在线程池中调用 C++
        success = await run_in_threadpool(
            native_core.make_thumbnail,
            str(file_path),
            str(thumb_path)
        )
        
        if success:
            # 更新数据库中的缩略图路径
            relative_thumb_path = str(thumb_path.relative_to(settings.PROJECT_ROOT))
            self.file_info.update_thumbnail_url(full_hash, relative_thumb_path)
            return relative_thumb_path
        
        return None

    def add_reference(self, full_hash: str) -> int:
        return self.file_info.increase_refer_count(full_hash)

    def remove_reference(self, full_hash: str) -> int:
        # [TODO] 当引用计数为 0 时，可以考虑物理删除文件
        return self.file_info.decrease_refer_count(full_hash)

    async def finalize_upload(self, temp_path: str, file_name: str, full_hash: str, mime_type: str) -> str:
        """从临时文件转存到正式目录并记录数据库"""
        sub_dir = full_hash[:2]
        save_dir = settings.STORAGE_ROOT / sub_dir
        save_dir.mkdir(parents=True, exist_ok=True)
        
        final_path = save_dir / full_hash
        file_size = os.path.getsize(temp_path)

        def _move():
            # 使用 shutil.move 支持跨文件系统
            shutil.move(temp_path, final_path)
        
        await run_in_threadpool(_move)
        
        # 记录数据库
        self.file_info.upsert_file(
            full_hash=full_hash,
            sparse_hash=None, 
            file_name=file_name,
            file_size=file_size,
            mime_type=mime_type,
            storage_path=str(final_path.relative_to(settings.PROJECT_ROOT)),
            thumbnail_url=None
        )
        
        return str(final_path)
