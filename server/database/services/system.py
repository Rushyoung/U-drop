import uuid

from server.core.config import settings
from server.core.logger import logger
from server.core.system_guard import SystemGuard
from server.database.models import (
    Attachment,
    Device,
    FileInfo,
    Hashtag,
    Message,
    MessageTag,
    Session,
    Share,
    SysSetting,
    UploadTask,
    User,
)
from server.database.services.utils import AuthManager, get_time


class SystemService:
    def _trigger_guard_sync(self):
        SystemGuard.sync(self.get_all_settings_dict(), self.has_admin())

    def has_admin(self) -> bool:
        return User.select().where(User.role == "admin").exists()

    def get_all_settings_dict(self) -> dict[str, str]:
        rows = SysSetting.select()
        return {row.key: row.value for row in rows}

    def get_setting(self, key: str, default: str = "") -> str:
        row = SysSetting.get_or_none(SysSetting.key == key)
        return row.value if row else default

    def set_setting(self, key: str, value: str):
        (SysSetting.insert(key=key, value=value).on_conflict("replace").execute())

    def get_status(self) -> dict:
        return {
            "initialized": self.has_admin(),
            "version": "0.5.1",
            "allow_registration": self.get_setting("allow_registration", "true")
            == "true",
            "auth_rate_limit": int(self.get_setting("auth_rate_limit", "5")),
            "default_token_expire": int(
                self.get_setting("default_token_expire", "86400")
            ),
        }

    def initialize_system(
        self,
        account: str,
        password: str,
        allow_registration: bool,
        auth_rate_limit: int = 5,
        default_token_expire: int = 86400,
    ) -> bool:
        if self.has_admin():
            logger.warning("系统初始化尝试被拦截：管理员已存在")
            return False

        admin_uuid = str(uuid.uuid4())
        password_hash = AuthManager.get_password_hash(password)
        User.create(
            uuid=admin_uuid,
            account=account,
            password_hash=password_hash,
            created_at=get_time(),
            role="admin",
        )

        self.set_setting(
            "allow_registration", "true" if allow_registration else "false"
        )
        self.set_setting("auth_rate_limit", str(auth_rate_limit))
        self.set_setting("default_token_expire", str(default_token_expire))

        self._trigger_guard_sync()
        logger.success(f"系统初始化完成！管理员账号: {account}")
        return True

    def update_settings(
        self,
        allow_registration: bool | None,
        auth_rate_limit: int | None = None,
        default_token_expire: int | None = None,
    ):
        if allow_registration is not None:
            self.set_setting(
                "allow_registration", "true" if allow_registration else "false"
            )
        if auth_rate_limit is not None:
            self.set_setting("auth_rate_limit", str(auth_rate_limit))
        if default_token_expire is not None:
            self.set_setting("default_token_expire", str(default_token_expire))
        self._trigger_guard_sync()
        logger.info(
            f"系统配置更新 | allow_reg={allow_registration}, rate_limit={auth_rate_limit}, expire={default_token_expire}"
        )

    def factory_reset(self):
        import os
        import shutil

        for item in settings.STORAGE_ROOT.iterdir():
            if item.is_dir():
                if item.name not in ["temp", "thumbnails"]:
                    shutil.rmtree(item)
                else:
                    for sub in item.iterdir():
                        if sub.is_file():
                            os.remove(sub)
                        elif sub.is_dir():
                            shutil.rmtree(sub)
            else:
                os.remove(item)

        for model in [
            Attachment,
            Share,
            MessageTag,
            Hashtag,
            Message,
            FileInfo,
            Session,
            Device,
            User,
            UploadTask,
        ]:
            model.delete().execute()

        User._meta.database.execute_sql("DELETE FROM sqlite_sequence")

        self._trigger_guard_sync()
        logger.warning("系统已执行工厂重置，所有数据已清空。")
