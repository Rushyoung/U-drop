from db.repositories.file_info import FileInfoRepository


class FileService:
    def __init__(self, file_info: FileInfoRepository) -> None:
        self.file_info = file_info

    def register_file(
        self,
        full_hash: str,
        sparse_hash: str | None,
        file_name: str,
        file_size: int,
        mime_type: str | None,
        storage_path: str,
        thumbnail_url: str | None = None,
    ) -> None:
        raise NotImplementedError

    def add_reference(self, full_hash: str) -> int:
        raise NotImplementedError

    def remove_reference(self, full_hash: str) -> int:
        raise NotImplementedError