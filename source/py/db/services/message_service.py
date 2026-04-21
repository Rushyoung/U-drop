from db.repositories.file_info import FileInfoRepository
from db.repositories.hashtags import HashtagRepository
from db.repositories.message_tags import MessageTagRepository
from db.repositories.messages import MessageRepository


class MessageService:
    def __init__(
        self,
        messages: MessageRepository,
        file_info: FileInfoRepository,
        hashtags: HashtagRepository,
        message_tags: MessageTagRepository,
    ) -> None:
        self.messages = messages
        self.file_info = file_info
        self.hashtags = hashtags
        self.message_tags = message_tags

    def create_message(
        self,
        sender_uuid: str,
        device_id: str,
        message_type: int,
        content: str | None,
        file_hash: str | None,
        timestamp: int,
        tag_names: list[str] | None = None,
    ) -> int:
        raise NotImplementedError

    def delete_message(self, message_id: int) -> None:
        raise NotImplementedError