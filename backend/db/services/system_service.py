from db.repositories.system import SystemRepository
from db.repositories.users import UserRepository
from db.services.utils import AuthManager, get_time
import uuid
from core.logger import logger
from core.system_guard import SystemGuard

class SystemService:
    def __init__(self, system_repo: SystemRepository, user_repo: UserRepository) -> None:
        self.system_repo = system_repo
        self.user_repo = user_repo

    def _trigger_guard_sync(self):
        """内部辅助：将最新配置同步至内存卫兵"""
        SystemGuard.sync(self.system_repo.get_all_settings(), self.user_repo.has_admin())

    def get_status(self) -> dict:
        """获取系统初始化状态及基础配置"""
        return {
            "initialized": self.user_repo.has_admin(),
            "version": "0.5.1",
            "allow_registration": self.system_repo.get_setting("allow_registration", "true") == "true",
            "auth_rate_limit": int(self.system_repo.get_setting("auth_rate_limit", "5")),
            "default_token_expire": int(self.system_repo.get_setting("default_token_expire", "86400"))
        }

    def initialize_system(self, account: str, password: str, allow_registration: bool, auth_rate_limit: int = 5, default_token_expire: int = 86400) -> bool:
        """一键初始化：创建管理员并设置初态"""
        if self.user_repo.has_admin():
            logger.warning("系统初始化尝试被拦截：管理员已存在")
            return False
        
        # 1. 创建超级管理员
        admin_uuid = str(uuid.uuid4())
        password_hash = AuthManager.get_password_hash(password)
        self.user_repo.create_user(
            uuid=admin_uuid,
            account=account,
            password_hash=password_hash,
            created_at=get_time(),
            role='admin'
        )
        
        # 2. 设置系统初始配置
        self.system_repo.set_setting("allow_registration", "true" if allow_registration else "false")
        self.system_repo.set_setting("auth_rate_limit", str(auth_rate_limit))
        self.system_repo.set_setting("default_token_expire", str(default_token_expire))
        
        # 实时同步至内存卫兵
        self._trigger_guard_sync()
        
        logger.success(f"🚀 系统初始化完成！管理员账号: {account}")
        return True

    def update_settings(self, allow_registration: bool | None, auth_rate_limit: int | None = None, default_token_expire: int | None = None):
        """管理员修改系统动态配置"""
        if allow_registration is not None:
            self.system_repo.set_setting("allow_registration", "true" if allow_registration else "false")
        
        if auth_rate_limit is not None:
            self.system_repo.set_setting("auth_rate_limit", str(auth_rate_limit))

        if default_token_expire is not None:
            self.system_repo.set_setting("default_token_expire", str(default_token_expire))

        self._trigger_guard_sync() # 实时刷新内存卫兵
        logger.info(f"系统配置更新 | allow_reg={allow_registration}, rate_limit={auth_rate_limit}, expire={default_token_expire}")

    def factory_reset(self, conn):
        """高危：重置系统数据"""
        # 1. 物理清理：删除 storage 和 thumbnails 下的所有文件
        import shutil
        import os
        from core.config import settings
        
        # 清理 storage (保留 temp 和 thumbnails 目录本身)
        for item in settings.STORAGE_ROOT.iterdir():
            if item.is_dir():
                if item.name not in ["temp", "thumbnails"]:
                    shutil.rmtree(item)
                else:
                    # 清理子目录内容
                    for sub in item.iterdir():
                        if sub.is_file(): os.remove(sub)
                        elif sub.is_dir(): shutil.rmtree(sub)
            else:
                os.remove(item)
        
        # 2. 数据库重置：清空除 sys_settings 之外的所有业务表
        tables = [
            "attachments", "shares", "messages_tags", "hashtags", 
            "messages", "file_info", "sessions", "devices", "users"
        ]
        for table in tables:
            conn.execute(f"DELETE FROM {table}")
        
        # 3. 释放自增 ID
        conn.execute("DELETE FROM sqlite_sequence")
        
        # 刷新内存卫兵状态（回到未初始化）
        self._trigger_guard_sync()
        
        logger.warning("🚨 系统已执行工厂重置，所有数据已清空。")
