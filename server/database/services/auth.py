import secrets
import uuid
from threading import Lock

from server.core.exceptions import (
    AccountRepeat,
    ForbiddenError,
    LoginError,
    TokenExpired,
)
from server.core.logger import logger
from server.database.models import Attachment, Device, FileInfo, Message, Session, User
from server.database.services.utils import ONE_DAY, AuthManager, get_time
from server.schemas.auth import LoginData

_SESSION_CACHE: dict[str, dict] = {}
_SESSION_LOCK = Lock()
MAX_SESSION_CACHE_SIZE = 5000


def _update_cache_safe(token: str, info: dict | None):
    with _SESSION_LOCK:
        if info is None:
            _SESSION_CACHE.pop(token, None)
            return
        if (
            token not in _SESSION_CACHE
            and len(_SESSION_CACHE) >= MAX_SESSION_CACHE_SIZE
        ):
            try:
                oldest_key = next(iter(_SESSION_CACHE))
                _SESSION_CACHE.pop(oldest_key)
                logger.debug(
                    f"Session GC | 达到上限，弹出最旧缓存: {oldest_key[:10]}..."
                )
            except StopIteration:
                pass
        _SESSION_CACHE[token] = info


class AuthService:
    def register_user(self, account: str, plain_password: str) -> bool:
        if not User.select().where(User.account == account).exists():
            user_uuid = str(uuid.uuid4())
            password_hash = AuthManager.get_password_hash(plain_password)
            User.create(
                uuid=user_uuid,
                account=account,
                password_hash=password_hash,
                created_at=get_time(),
            )
            logger.info(f"新用户注册: {account} (UUID: {user_uuid})")
            return True
        raise AccountRepeat

    def login(
        self,
        account: str,
        password: str,
        device_id: str,
        device_type: int,
        device_name: str | None,
        expire_in: int | None = None,
        single_use: bool = False,
        remember_me: bool = False,
        **kwargs,
    ) -> LoginData:
        info = User.get_or_none(User.account == account)
        if info is None:
            AuthManager.get_password_hash("dummy_password")
            logger.warning(f"登录失败: 账号不存在 -> {account}")
            raise LoginError

        if not info.is_active:
            AuthManager.get_password_hash("dummy_password")
            logger.warning(f"登录失败: 账号已被禁用 -> {account}")
            raise ForbiddenError("Account is disabled")

        if not AuthManager.verify_password_hash(password, info.password_hash):
            logger.warning(f"登录失败: 密码错误 -> {account}")
            raise LoginError

        row = Session.get_or_none(
            (Session.user_uuid == info.uuid) & (Session.device_id == device_id)
        )

        is_sliding = 1 if remember_me else 0
        MAX_EXPIRE = ONE_DAY * 365

        if expire_in:
            req_duration = expire_in
        elif remember_me:
            req_duration = info.sliding_window_days * ONE_DAY
        else:
            req_duration = min(info.temp_expire_hours, 24) * 3600

        actual_duration = min(req_duration, MAX_EXPIRE)
        expire_at = get_time() + actual_duration

        if row is None or single_use:
            token = secrets.token_urlsafe(32)
            Session.create(
                bearer_token=token,
                user_uuid=info.uuid,
                device_id=device_id,
                expire_time=expire_at,
                is_single_use=(1 if single_use else 0),
                is_sliding=is_sliding,
            )
            Device.insert(
                device_id=device_id,
                user_uuid=info.uuid,
                device_type=device_type,
                device_name=device_name or "未知设备名称",
                last_seen=get_time(),
            ).on_conflict("replace").execute()
            logger.info(
                f"登录成功 | 用户: {account} | 创建新 Session | 有效期: {actual_duration}s | Sliding: {is_sliding}"
            )
        else:
            token = row.bearer_token
            (
                Session.update(expire_time=expire_at, is_sliding=is_sliding)
                .where(Session.bearer_token == token)
                .execute()
            )
            logger.info(
                f"登录成功 | 用户: {account} | 刷新现有 Session | 新有效期: {actual_duration}s | Sliding: {is_sliding}"
            )

        row = Session.get_or_none(Session.bearer_token == token)
        _update_cache_safe(token, dict(row) if row else None)

        return LoginData(bearer=token)

    def is_active_user(
        self, bearer: str, now: int = get_time(), expire_enable: bool = False
    ):
        with _SESSION_LOCK:
            info = _SESSION_CACHE.get(bearer)

        if info:
            logger.debug(f"Session 缓存命中: {bearer[:10]}...")
        else:
            row = Session.get_or_none(Session.bearer_token == bearer)
            if row:
                info = dict(row)
                _update_cache_safe(bearer, info)
                logger.debug(f"Session 缓存回填 (查库成功): {bearer[:10]}...")
            else:
                logger.warning(f"Session 校验失败: Token 不存在 -> {bearer[:10]}...")
                raise TokenExpired

        user_info = User.get_or_none(User.uuid == info["user_uuid"])
        if not user_info or not user_info.is_active:
            logger.warning(
                f"Session 熔断: 关联用户已禁用或不存在 -> {info['user_uuid'][:8]}"
            )
            self.logout(bearer)
            raise TokenExpired

        if expire_enable:
            if info["expire_time"] < now:
                logger.warning(
                    f"Session 已过期: {bearer[:10]}... (到期: {info['expire_time']}, 当前: {now})"
                )
                self.logout(bearer)
                raise TokenExpired

        if info.get("is_sliding") == 1:
            window_seconds = user_info.sliding_window_days * ONE_DAY
            remaining = info["expire_time"] - now
            if remaining < (window_seconds // 2):
                new_expire = now + window_seconds
                (
                    Session.update(expire_time=new_expire)
                    .where(Session.bearer_token == bearer)
                    .execute()
                )
                updated_info = dict(info)
                updated_info["expire_time"] = new_expire
                _update_cache_safe(bearer, updated_info)
                logger.info(
                    f"Session 自动滑动续期 | 用户: {user_info.account} | 延长至: {user_info.sliding_window_days}天后"
                )

        if info["is_single_use"] == 1:
            logger.info(f"!!! 一次性 Token 被消费，立即销毁: {bearer[:10]}...")
            self.logout(bearer)

        return info

    def logout(self, bearer_token: str) -> None:
        with _SESSION_LOCK:
            _SESSION_CACHE.pop(bearer_token, None)
        count = Session.delete().where(Session.bearer_token == bearer_token).execute()
        if count > 0:
            logger.info(f"Session 已注销: {bearer_token[:10]}...")
        else:
            logger.warning(f"注销失败: Token 不存在或已失效 -> {bearer_token[:10]}...")
            raise TokenExpired

    def get_user_by_uuid(self, user_uuid: str):
        return User.get_or_none(User.uuid == user_uuid)

    def update_user_settings(
        self,
        user_uuid: str,
        trash_expire_days: int | None = None,
        temp_expire_hours: int | None = None,
        sliding_window_days: int | None = None,
    ):
        logger.info(
            f"用户 {user_uuid[:8]} 更新设置: trash={trash_expire_days}, temp={temp_expire_hours}, sliding={sliding_window_days}"
        )
        updates = {}
        if trash_expire_days is not None:
            updates["trash_expire_days"] = trash_expire_days
        if temp_expire_hours is not None:
            updates["temp_expire_hours"] = temp_expire_hours
        if sliding_window_days is not None:
            updates["sliding_window_days"] = sliding_window_days
        if not updates:
            return 0
        return User.update(**updates).where(User.uuid == user_uuid).execute()

    def update_device_name(self, device_id: str, device_name: str):
        logger.info(f"更新设备 {device_id[:8]} 名称为: {device_name}")
        return (
            Device.update(device_name=device_name)
            .where(Device.device_id == device_id)
            .execute()
        )

    def touch_device(self, device_id: str):
        return (
            Device.update(last_seen=get_time())
            .where(Device.device_id == device_id)
            .execute()
        )

    def list_user_devices(self, user_uuid: str) -> list[dict]:
        rows = (
            Device.select(Device)
            .join(Session, on=(Device.device_id == Session.device_id))
            .where(Device.user_uuid == user_uuid)
            .distinct()
            .execute()
        )
        return [dict(r) for r in rows]

    def revoke_device(self, user_uuid: str, device_id: str) -> bool:
        device = Device.get_or_none(Device.device_id == device_id)
        if not device or device.user_uuid != user_uuid:
            logger.warning(
                f"设备下线失败 | 设备 {device_id[:8]} 不属于用户 {user_uuid[:8]}"
            )
            return False

        with _SESSION_LOCK:
            cache_keys = list(_SESSION_CACHE.keys())
            kicked_count = 0
            for tk in cache_keys:
                if _SESSION_CACHE[tk].get("device_id") == device_id:
                    _SESSION_CACHE.pop(tk, None)
                    kicked_count += 1

        Session.delete().where(Session.device_id == device_id).execute()

        logger.warning(
            f"设备已下线 | 用户 {user_uuid[:8]} 使得设备 {device_id[:8]} ({device['device_name']}) 的会话失效。清理了 {kicked_count} 个 Token。"
        )
        return True

    def admin_update_quota(self, admin_uuid: str, target_uuid: str, storage_quota: int):
        logger.info(
            f"审计 | 管理员 {admin_uuid[:8]} 修改用户 {target_uuid[:8]} 配额为 {storage_quota} Bytes"
        )
        return (
            User.update(storage_quota=storage_quota)
            .where(User.uuid == target_uuid)
            .execute()
        )

    def admin_update_status(self, admin_uuid: str, target_uuid: str, is_active: bool):
        if admin_uuid == target_uuid:
            raise ForbiddenError("Admin cannot disable themselves.")

        logger.info(
            f"审计 | 管理员 {admin_uuid[:8]} 设置用户 {target_uuid[:8]} 状态为 {'启用' if is_active else '禁用'}"
        )

        if not is_active:
            with _SESSION_LOCK:
                cache_keys = list(_SESSION_CACHE.keys())
                for tk in cache_keys:
                    if _SESSION_CACHE[tk]["user_uuid"] == target_uuid:
                        _SESSION_CACHE.pop(tk, None)
                        Session.delete().where(Session.bearer_token == tk).execute()
            logger.info(f"审计 | 用户 {target_uuid[:8]} 已被强制下线")

        return (
            User.update(is_active=1 if is_active else 0)
            .where(User.uuid == target_uuid)
            .execute()
        )

    def admin_hard_delete_user(self, admin_uuid: str, target_uuid: str):
        if admin_uuid == target_uuid:
            raise LoginError()

        user = User.get_or_none(User.uuid == target_uuid)
        if not user:
            return

        logger.warning(
            f"审计 | 管理员 {admin_uuid[:8]} 正在物理销毁用户: {user.account} ({target_uuid[:8]})"
        )

        rows = (
            Attachment.select(Attachment.file_hash)
            .join(Message, on=(Attachment.message_id == Message.id))
            .where(Message.sender_uuid == target_uuid)
            .execute()
        )
        hashes = [r.file_hash for r in rows]

        if hashes:
            for h in hashes:
                (
                    FileInfo.update(refer_count=FileInfo.refer_count - 1)
                    .where(FileInfo.full_hash == h)
                    .execute()
                )
            logger.info(f"审计 | 已核减用户 {len(hashes)} 个物理文件引用计数")

        with _SESSION_LOCK:
            cache_keys = list(_SESSION_CACHE.keys())
            kicked_count = 0
            for tk in cache_keys:
                if _SESSION_CACHE[tk]["user_uuid"] == target_uuid:
                    _SESSION_CACHE.pop(tk, None)
                    kicked_count += 1

        User.delete().where(User.uuid == target_uuid).execute()
        logger.success(f"审计 | 用户销毁完成。清理了 {kicked_count} 个活跃 Session。")

    def change_password(self, user_uuid: str, old_password: str, new_password: str):
        user = User.get_or_none(User.uuid == user_uuid)
        if not user or not AuthManager.verify_password_hash(
            old_password, user.password_hash
        ):
            logger.warning(f"密码修改失败 | 用户 {user_uuid[:8]} 旧密码验证不通过")
            raise LoginError()

        new_hash = AuthManager.get_password_hash(new_password)
        User.update(password_hash=new_hash).where(User.uuid == user_uuid).execute()
        logger.success(f"密码修改成功 | 用户 {user_uuid[:8]}")

    @staticmethod
    def clean_expired_sessions():
        now = get_time()
        with _SESSION_LOCK:
            cache_keys = list(_SESSION_CACHE.keys())
            expired_count = 0

            for tk in cache_keys:
                info = _SESSION_CACHE.get(tk)
                if info and info["expire_time"] < now:
                    _SESSION_CACHE.pop(tk, None)
                    expired_count += 1

        if expired_count > 0:
            logger.info(f"GC | 已从内存缓存清理 {expired_count} 个过期 Session")
