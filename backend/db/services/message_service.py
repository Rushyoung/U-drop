import time
import html
from typing import Optional, List
from db.repositories.file_info import FileInfoRepository
from db.repositories.hashtags import HashtagRepository
from db.repositories.message_tags import MessageTagRepository
from db.repositories.messages import MessageRepository
from db.repositories.attachments import AttachmentRepository
from db.repositories.users import UserRepository
from core.uploads_manager import uploads_manager
from schemas.messages import (
    MessageResponse, FileInfoShort, PendingUploadResponse, 
    AttachmentResponse, BigFileResponse, BigFileReference
)
from core.exceptions import ForbiddenError, HashMismatch
from core.logger import logger

class MessageService:
    def __init__(
        self,
        messages: MessageRepository,
        file_info: FileInfoRepository,
        hashtags: HashtagRepository,
        message_tags: MessageTagRepository,
        attachments: AttachmentRepository,
        users: UserRepository
    ) -> None:
        self.messages = messages
        self.file_info = file_info
        self.hashtags = hashtags
        self.message_tags = message_tags
        self.attachments = attachments
        self.users = users

    def create_message(
        self,
        sender_uuid: str,
        device_id: str,
        message_type: int,
        content: Optional[str],
        timestamp: int,
        tag_names: Optional[List[str]] = None,
        file_hash: Optional[str] = None,
        file_name: Optional[str] = None,
    ) -> int:
        """创建消息"""
        # 安全加固：对文本内容进行 HTML 转义防止 XSS
        safe_content = html.escape(content) if content else None

        message_id = self.messages.create_message(
            sender_uuid=sender_uuid,
            device_id=device_id,
            message_type=message_type,
            content=safe_content,
            timestamp=timestamp
        )

        if file_hash:
            self.attachments.add_attachment(
                message_id=message_id,
                file_hash=file_hash,
                display_name=file_name or "未命名文件"
            )

        if tag_names:
            # [TODO] 标签逻辑
            pass

        return message_id

    def list_timeline(self, user_uuid: str, **kwargs) -> List[MessageResponse]:
        rows = self.messages.list_messages(user_uuid=user_uuid, **kwargs)
        return self._aggregate_attachments(rows)

    def list_trash(self, user_uuid: str) -> List[MessageResponse]:
        """列出回收站内容"""
        rows = self.messages.list_trash(user_uuid)
        return self._aggregate_attachments(rows)

    def _aggregate_attachments(self, rows) -> List[MessageResponse]:
        """内部辅助：聚合附件和内存任务数据"""
        if not rows: return []
        message_ids = [row['id'] for row in rows]
        attach_rows = self.attachments.list_by_message_ids(message_ids)
        
        attach_map = {}
        for ar in attach_rows:
            m_id = ar['message_id']
            if m_id not in attach_map: attach_map[m_id] = []
            attach_map[m_id].append(ar)

        results = []
        for row in rows:
            msg_dict = dict(row)
            m_id = msg_dict['id']
            msg_dict['attachments'] = []
            if m_id in attach_map:
                for ar in attach_map[m_id]:
                    msg_dict['attachments'].append({
                        "id": ar['id'],
                        "file_hash": ar['file_hash'],
                        "display_name": ar['display_name'],
                        "file_info": {
                            "full_hash": ar['file_hash'],
                            "file_size": ar['file_size'],
                            "mime_type": ar['mime_type']
                        }
                    })
            
            pending_tasks = uploads_manager.list_by_message_id(m_id)
            msg_dict['pending_uploads'] = [
                PendingUploadResponse(
                    upload_id=t.upload_id,
                    file_name=t.file_name,
                    received_size=t.received_size,
                    total_size=t.total_size,
                    mime_type=t.mime_type
                ) for t in pending_tasks
            ]
            msg_dict['tags'] = []
            results.append(MessageResponse.model_validate(msg_dict))
        return results

    def bind_file_to_message(self, user_uuid: str, message_id: int, file_hash: str, display_name: str):
        """将物理文件绑定至具体消息附件 (真实 CAS 计费)"""
        # 1. 计费判定：判断该用户是否已在为该哈希“买单” (含正常及回收站)
        is_paying = self.attachments.check_user_has_file(user_uuid, file_hash)
        
        # 2. 绑定附件记录 (Repository 内部会增加全局 refer_count)
        self.attachments.add_attachment(message_id, file_hash, display_name)
        
        # 3. 如果是该用户新引用的文件哈希，则扣减配额
        if not is_paying:
            file_info = self.file_info.get_by_full_hash(file_hash)
            if file_info:
                self.users.update_used_storage(user_uuid, file_info['file_size'])
                logger.info(f"计费 | 用户 {user_uuid[:8]} 为新哈希支付配额: {file_info['file_size']} Bytes")
        else:
            logger.info(f"计费 | 用户 {user_uuid[:8]} 秒传复用已有引用，不重复扣费")

    def detach_attachment_safe(self, user_uuid: str, message_id: int, attachment_id: int):
        """安全剥离附件：处理配额返还、引用核减及空消息清理"""
        # 安全修复：验证消息归属权，防止越权剥离他人附件
        msg_row = self.messages.get_by_id(message_id)
        if not msg_row or msg_row['sender_uuid'] != user_uuid:
            logger.warning(f"越权告警 | 用户 {user_uuid[:8]} 试图剥离不属于他的消息附件: MessageID={message_id}")
            return False

        # 1. 确认附件归属及哈希
        attach_rows = self.attachments.list_by_message_id(message_id)
        target_attach = next((dict(r) for r in attach_rows if r['id'] == attachment_id), None)
        if not target_attach: return False
        
        file_hash = target_attach['file_hash']
        file_size = target_attach['file_size']

        # 2. 执行物理剥离 (Repository 会核减全局 refer_count)
        self.attachments.delete_attachment(attachment_id)
        logger.info(f"清理 | 附件 {attachment_id} 已从消息 {message_id} 剥离")

        # 3. 计费返还判定：如果该用户名下已无该哈希的任何有效引用，则返还配额
        if not self.attachments.check_user_has_file(user_uuid, file_hash):
            self.users.update_used_storage(user_uuid, -file_size)
            logger.success(f"计费 | 用户 {user_uuid[:8]} 已彻底释放哈希引用，配额返还: {file_size} Bytes")

        # 4. 空消息自动清理：若附件清空且无文本内容，则整条删除
        remaining = self.attachments.list_by_message_id(message_id)
        if not remaining and (not msg_row['content'] or not msg_row['content'].strip()):
            self.messages.hard_delete_message(message_id)
            logger.info(f"清理 | 消息 {message_id} 因内容为空已被自动清除")
        
        return True

    def _hard_delete_single(self, message_id: int, user_uuid: str):
        """内部辅助：物理删除单条消息及其附件，适配 CAS 计费"""
        attachs = self.attachments.list_by_message_id(message_id)
        
        for a in attachs:
            a_id = a['id']
            # 使用安全剥离逻辑来处理配额退回
            self.detach_attachment_safe(user_uuid, message_id, a_id)

    def restore_message(self, message_id: int, user_uuid: str):
        """从回收站恢复"""
        msg = self.messages.get_by_id(message_id)
        if not msg or msg['sender_uuid'] != user_uuid:
            raise ForbiddenError("消息不存在或无权恢复")
        return self.messages.restore_message(message_id)

    def empty_user_trash(self, user_uuid: str) -> int:
        """清空该用户的所有回收站记录（物理删除并释放配额）"""
        trash_ids = self.messages.get_user_trash_ids(user_uuid)
        count = 0
        for mid in trash_ids:
            self._hard_delete_single(mid, user_uuid)
            count += 1
        return count

    def delete_message(self, message_id: int) -> bool:
        """软删除逻辑：不再立即清理附件，保留引用直到彻底删除"""
        return self.messages.soft_delete_message(message_id) > 0

    def list_large_files(self, user_uuid: str, limit: int = 20) -> List[BigFileResponse]:
        """大文件猎手：拉取占用最大的文件清单及当前用户的详细引用清单"""
        rows = self.attachments.list_user_large_files(user_uuid, limit)
        
        results = []
        for r in rows:
            refs = []
            # 解析聚合字符串 "msg_id:attach_id:display_name|..."
            if r['ref_info']:
                for ref_str in r['ref_info'].split('|'):
                    parts = ref_str.split(':', 2)
                    if len(parts) == 3:
                        refs.append(BigFileReference(
                            message_id=int(parts[0]),
                            attachment_id=int(parts[1]),
                            display_name=parts[2]
                        ))
            
            results.append(BigFileResponse(
                full_hash=r['full_hash'],
                file_size=r['file_size'],
                mime_type=r['mime_type'],
                refer_count=r['refer_count'],
                references=refs
            ))
        return results
