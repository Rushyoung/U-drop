import os
from pathlib import Path
from typing import Optional, Tuple
from fastapi.concurrency import run_in_threadpool
from db.repositories.file_info import FileInfoRepository
from core.native_wrapper import native_core
from core.config import settings
import shutil
from core.logger import logger

class FileService:
    def __init__(self, file_info: FileInfoRepository) -> None:
        self.file_info = file_info

    def get_file_by_hash(self, full_hash: str):
        return self.file_info.get_by_full_hash(full_hash)

    def _resolve_local_path(self, storage_path: str) -> Optional[Path]:
        """将 local:// 协议路径解析为绝对物理路径"""
        if storage_path.startswith("local://"):
            rel_path = storage_path.replace("local://", "")
            return settings.STORAGE_ROOT / rel_path
        return None

    async def get_physical_path_and_name(self, full_hash: str) -> Tuple[Optional[Path], str]:
        """获取物理路径（用于下载），由于重构后文件信息不含名称，此处返回哈希作为默认名"""
        info = self.file_info.get_by_full_hash(full_hash)
        if not info:
            return None, "unknown"
        
        path = self._resolve_local_path(info['storage_path'])
        return path, full_hash # 默认返回哈希，真正的业务文件名应由附件表提供

    async def finalize_upload(self, temp_path: str, full_hash: str, sparse_hash: str, mime_type: str) -> str:
        """从临时文件转存到正式目录并记录物理元数据"""
        sub_dir = full_hash[:2]
        save_dir = settings.STORAGE_ROOT / sub_dir
        save_dir.mkdir(parents=True, exist_ok=True)
        
        final_path = save_dir / full_hash
        file_size = await run_in_threadpool(os.path.getsize, temp_path)

        def _move():
            shutil.move(temp_path, final_path)
        await run_in_threadpool(_move)
        
        # 记录物理信息 (不再存业务文件名)
        self.file_info.upsert_file(
            full_hash=full_hash,
            sparse_hash=sparse_hash, 
            file_size=file_size,
            mime_type=mime_type,
            storage_path=f"local://{sub_dir}/{full_hash}"
        )
        return str(final_path)

    async def get_or_create_thumbnail(self, full_hash: str) -> str | None:
        thumb_path = settings.THUMBNAIL_ROOT / f"{full_hash}.jpg"
        if thumb_path.exists():
            return str(thumb_path)

        file_row = self.file_info.get_by_full_hash(full_hash)
        if not file_row:
            return None
        
        abs_src_path = self._resolve_local_path(file_row['storage_path'])
        if abs_src_path and abs_src_path.exists():
            success = await run_in_threadpool(
                native_core.make_thumbnail,
                str(abs_src_path),
                str(thumb_path)
            )
            return str(thumb_path) if success else None
        
        return None

    async def cleanup_orphan_files(self) -> int:
        """扫描并物理删除所有引用计数归零的文件及其缩略图"""
        orphans = self.file_info.list_orphans()
        count = 0
        for row in orphans:
            full_hash = row['full_hash']
            storage_path = row['storage_path']
            
            # 1. 删除原文件
            abs_path = self._resolve_local_path(storage_path)
            if abs_path and abs_path.exists():
                try:
                    await run_in_threadpool(os.remove, abs_path)
                    logger.info(f"GC | 物理删除孤儿文件: {full_hash[:16]}...")
                except Exception as e:
                    logger.error(f"GC | 删除文件失败: {e}")

            # 2. 删除缩略图 (如果存在)
            thumb_path = settings.THUMBNAIL_ROOT / f"{full_hash}.jpg"
            if thumb_path.exists():
                try:
                    await run_in_threadpool(os.remove, thumb_path)
                    logger.debug(f"GC | 清理缩略图: {full_hash[:16]}...")
                except Exception as e:
                    logger.error(f"GC | 删除缩略图失败: {e}")

            # 3. 删除数据库记录
            self.file_info.delete_file_info(full_hash)
            count += 1
            
        return count
