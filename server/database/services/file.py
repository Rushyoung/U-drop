import os
from pathlib import Path
from typing import Optional, Tuple

from fastapi.concurrency import run_in_threadpool

from server.core.config import settings
from server.core.logger import logger
from server.core.native_wrapper import native_core
from server.database.models import FileInfo


class FileService:
    def get_file_by_hash(self, full_hash: str):
        return FileInfo.get_or_none(FileInfo.full_hash == full_hash)

    @staticmethod
    def _resolve_local_path(storage_path: str) -> Optional[Path]:
        if storage_path.startswith("local://"):
            rel_path = storage_path.replace("local://", "")
            return settings.STORAGE_ROOT / rel_path
        return None

    async def get_physical_path_and_name(
        self, full_hash: str
    ) -> Tuple[Optional[Path], str]:
        info = FileInfo.get_or_none(FileInfo.full_hash == full_hash)
        if not info:
            return None, "unknown"
        path = self._resolve_local_path(info.storage_path)
        return path, full_hash

    async def finalize_upload(
        self, temp_path: str, full_hash: str, sparse_hash: str, mime_type: str
    ) -> str:
        sub_dir = full_hash[:2]
        save_dir = settings.STORAGE_ROOT / sub_dir
        save_dir.mkdir(parents=True, exist_ok=True)

        final_path = save_dir / full_hash
        file_size = await run_in_threadpool(os.path.getsize, temp_path)

        def _move():
            os.replace(temp_path, final_path)

        await run_in_threadpool(_move)

        (
            FileInfo.insert(
                full_hash=full_hash,
                sparse_hash=sparse_hash,
                file_size=file_size,
                mime_type=mime_type,
                storage_path=f"local://{sub_dir}/{full_hash}",
                refer_count=0,
            )
            .on_conflict("replace")
            .execute()
        )
        return str(final_path)

    async def get_or_create_thumbnail(self, full_hash: str) -> str | None:
        thumb_path = settings.THUMBNAIL_ROOT / f"{full_hash}.jpg"
        if thumb_path.exists():
            return str(thumb_path)

        file_row = FileInfo.get_or_none(FileInfo.full_hash == full_hash)
        if not file_row:
            return None

        abs_src_path = self._resolve_local_path(file_row.storage_path)
        if abs_src_path and abs_src_path.exists():
            success = await run_in_threadpool(
                native_core.make_thumbnail, str(abs_src_path), str(thumb_path)
            )
            return str(thumb_path) if success else None

        return None

    async def cleanup_orphan_files(self) -> int:
        orphans = list(FileInfo.select().where(FileInfo.refer_count <= 0))
        count = 0
        for row in orphans:
            abs_path = self._resolve_local_path(row.storage_path)
            if abs_path and abs_path.exists():
                try:
                    await run_in_threadpool(os.remove, abs_path)
                    logger.info(f"GC | 物理删除孤儿文件: {row.full_hash[:16]}...")
                except Exception as e:
                    logger.error(f"GC | 删除文件失败: {e}")

            thumb_path = settings.THUMBNAIL_ROOT / f"{row.full_hash}.jpg"
            if thumb_path.exists():
                try:
                    await run_in_threadpool(os.remove, thumb_path)
                    logger.debug(f"GC | 清理缩略图: {row.full_hash[:16]}...")
                except Exception as e:
                    logger.error(f"GC | 删除缩略图失败: {e}")

            FileInfo.delete().where(FileInfo.full_hash == row.full_hash).execute()
            count += 1

        return count
