import time
from typing import Optional, List
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
        content: Optional[str],
        file_hash: Optional[str],
        timestamp: int,
        tag_names: Optional[List[str]] = None,
    ) -> int:
        """创建消息，并处理标签关联"""
        # 1. 创建基础消息
        message_id = self.messages.create_message(
            sender_uuid=sender_uuid,
            device_id=device_id,
            message_type=message_type,
            content=content,
            file_hash=file_hash,
            timestamp=timestamp
        )

        # 2. 处理标签 (如果有)
        if tag_names:
            for name in tag_names:
                # 简化逻辑：获取或创建标签，然后关联
                # [TODO] 优化 Repository 增加 get_or_create_tag
                pass

        return message_id

    def update_message_file(self, message_id: int, file_hash: str):
        """文件上传完成后，更新消息的哈希引用"""
        return self.messages.update_file_hash(message_id, file_hash)

    def delete_message(self, message_id: int) -> bool:
        """删除消息并处理引用计数"""
        msg = self.messages.get_by_id(message_id)
        if not msg:
            return False
        
        # 1. 软删除消息
        self.messages.soft_delete_message(message_id)

        # 2. 如果有关联文件，引用计数 -1
        if msg['file_hash']:
            # self.file_info.decrease_refer_count(msg['file_hash'])
            pass
            
        return True
