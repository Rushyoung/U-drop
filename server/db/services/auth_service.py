from db.repositories.devices import DeviceRepository
from db.repositories.sessions import SessionRepository
from db.repositories.users import UserRepository
from core.exceptions import AccountRepeat, LoginError, TokenExpired, ForbiddenError
from db.services.utils import AuthManager, ONE_DAY, get_time
from schemas.auth import LoginData
from core.logger import logger
from core.system_guard import SystemGuard
import secrets
import uuid

from threading import Lock

# 全局 Session 缓存与并发锁
_SESSION_CACHE = {}
_SESSION_LOCK = Lock()
MAX_SESSION_CACHE_SIZE = 5000  # 会话缓存条目上限

def _update_cache_safe(token: str, info: dict | None):
    """安全更新缓存，并执行容量限制清理 (FIFO)"""
    with _SESSION_LOCK:
        if info is None:
            _SESSION_CACHE.pop(token, None)
            return
        
        # 如果是新条目且达到上限，弹出最旧的一个 (Python 3.7+ dict 保持插入顺序)
        if token not in _SESSION_CACHE and len(_SESSION_CACHE) >= MAX_SESSION_CACHE_SIZE:
            try:
                oldest_key = next(iter(_SESSION_CACHE))
                _SESSION_CACHE.pop(oldest_key)
                logger.debug(f"Session GC | 达到上限，弹出最旧缓存: {oldest_key[:10]}...")
            except StopIteration:
                pass
        
        _SESSION_CACHE[token] = info

class AuthService:
    def __init__(
        self,
        users: UserRepository,
        devices: DeviceRepository,
        sessions: SessionRepository,
    ) -> None:
        self.users = users
        self.devices = devices
        self.sessions = sessions

    def register_user(
        self,
        account: str,
        plain_password: str,
    ) -> bool:
        if not self.users.check_account(account):
            user_uuid = str(uuid.uuid4())
            password_hash = AuthManager.get_password_hash(plain_password)
            self.users.create_user(
                account=account,
                uuid=user_uuid,
                password_hash=password_hash,
                created_at=get_time()
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
        **kwargs # 兼容旧参数
    ) -> LoginData:
        info = self.users.get_by_account(account)
        if info is None:
            # 安全加固：时序侧信道防范
            # 即使账号不存在，也执行一次假哈希运算拉平耗时
            AuthManager.get_password_hash("dummy_password")
            logger.warning(f"登录失败: 账号不存在 -> {account}")
            raise LoginError
        
        # 安全校验：用户是否被禁用
        if not info.is_active:
            # 同样执行假运算保持时序一致性
            AuthManager.get_password_hash("dummy_password")
            logger.warning(f"登录失败: 账号已被禁用 -> {account}")
            raise ForbiddenError("Account is disabled")

        if not AuthManager.verify_password_hash(password, info.password_hash):
            logger.warning(f"登录失败: 密码错误 -> {account}")
            raise LoginError
        
        # 查找现有会话
        row = self.sessions.get_by_user_and_device(info.uuid, device_id)
        
        # 计算新的过期时间 (优先顺序: 请求指定 > 用户设置)
        is_sliding = 1 if remember_me else 0
        MAX_EXPIRE = ONE_DAY * 365 # 长效上限 1 年
        
        if expire_in:
            req_duration = expire_in
        elif remember_me:
            # 长效登录：使用用户配置的滑动窗口天数
            req_duration = info.sliding_window_days * ONE_DAY
        else:
            # 临时登录：使用用户配置的小时数
            req_duration = min(info.temp_expire_hours, 24) * 3600
            
        actual_duration = min(req_duration, MAX_EXPIRE)
        expire_at = get_time() + actual_duration

        if row is None or single_use:
            # 创建全新的 Token
            token = secrets.token_urlsafe(32)
            self.sessions.create_session(
                token, info.uuid, device_id, expire_at, 
                is_single_use=(1 if single_use else 0),
                is_sliding=is_sliding
            )
            self.devices.create_device(
                device_id, info.uuid, device_type,
                device_name if device_name else "未知设备名称", get_time()
            )
            logger.info(f"登录成功 | 用户: {account} | 创建新 Session | 有效期: {actual_duration}s | Sliding: {is_sliding}")
        else:
            # 复用 Token 且刷新过期时间及滑动状态
            token = row["bearer_token"]
            self.conn_execute_raw(
                "UPDATE sessions SET expire_time = ?, is_sliding = ? WHERE bearer_token = ?",
                (expire_at, is_sliding, token)
            )
            logger.info(f"登录成功 | 用户: {account} | 刷新现有 Session | 新有效期: {actual_duration}s | Sliding: {is_sliding}")


        # 重新拿一次最新的 row 存入缓存
        row = self.sessions.get_by_token(token)
        _update_cache_safe(token, dict(row) if row else None)
        
        return LoginData(bearer=token)
    
    def conn_execute_raw(self, sql, params):
        """辅助函数：直接在当前连接执行 SQL"""
        self.sessions.conn.execute(sql, params)

    def is_active_user(
            self,
            bearer: str,
            now:    int = get_time(),
            expire_enable:  bool = False
    ):
        """校验并消费 Token，支持滑动窗口自动续期"""
        with _SESSION_LOCK:
            info = _SESSION_CACHE.get(bearer)
            
        if info:
            logger.debug(f"Session 缓存命中: {bearer[:10]}...")
        else:
            row = self.sessions.get_by_token(bearer)
            if row:
                info = dict(row)
                _update_cache_safe(bearer, info)
                logger.debug(f"Session 缓存回填 (查库成功): {bearer[:10]}...")
            else:
                logger.warning(f"Session 校验失败: Token 不存在 -> {bearer[:10]}...")
                raise TokenExpired
        
        # 1. 安全校验：用户状态
        user_info = self.users.get_by_uuid(info["user_uuid"])
        if not user_info or not user_info.is_active:
            logger.warning(f"Session 熔断: 关联用户已禁用或不存在 -> {info['user_uuid'][:8]}")
            self.logout(bearer)
            raise TokenExpired
            
        # 2. 过期校验
        if expire_enable:
            if info["expire_time"] < now:
                logger.warning(f"Session 已过期: {bearer[:10]}... (到期: {info['expire_time']}, 当前: {now})")
                self.logout(bearer)
                raise TokenExpired

        # 3. [核心] 滑动窗口自动续期
        if info.get("is_sliding") == 1:
            # 剩余寿命少于滑动窗口的一半时触发续期
            window_seconds = user_info.sliding_window_days * ONE_DAY
            remaining = info["expire_time"] - now
            if remaining < (window_seconds // 2):
                new_expire = now + window_seconds
                self.conn_execute_raw(
                    "UPDATE sessions SET expire_time = ? WHERE bearer_token = ?",
                    (new_expire, bearer)
                )
                # 同步更新内存缓存 (需创建新对象以防脏读)
                updated_info = dict(info)
                updated_info["expire_time"] = new_expire
                _update_cache_safe(bearer, updated_info)
                logger.info(f"Session 自动滑动续期 | 用户: {user_info.account} | 延长至: {user_info.sliding_window_days}天后")

        # 4. 一次性 Token 销毁
        if info["is_single_use"] == 1:
            logger.info(f"!!! 一次性 Token 被消费，立即销毁: {bearer[:10]}...")
            self.logout(bearer)
        
        return info

    def logout(self, bearer_token: str) -> None:
        with _SESSION_LOCK:
            _SESSION_CACHE.pop(bearer_token, None)
        count = self.sessions.delete_by_token(bearer_token)
        if count > 0:
            logger.info(f"Session 已注销: {bearer_token[:10]}...")
        else:
            logger.warning(f"注销失败: Token 不存在或已失效 -> {bearer_token[:10]}...")
            raise TokenExpired

    def get_user_by_uuid(self, user_uuid: str):
        """获取用户全量信息（含配额、设置）"""
        return self.users.get_by_uuid(user_uuid)

    def update_user_settings(self, user_uuid: str, trash_expire_days: int | None = None, temp_expire_hours: int | None = None, sliding_window_days: int | None = None):
        """更新用户个人偏好"""
        logger.info(f"用户 {user_uuid[:8]} 更新设置: trash={trash_expire_days}, temp={temp_expire_hours}, sliding={sliding_window_days}")
        return self.users.update_settings(user_uuid, trash_expire_days, temp_expire_hours, sliding_window_days)

    def update_device_name(self, device_id: str, device_name: str):
        """更新设备显示名称"""
        logger.info(f"更新设备 {device_id[:8]} 名称为: {device_name}")
        return self.devices.update_device_name(device_id, device_name)

    def touch_device(self, device_id: str):
        """更新设备最后活跃时间 (心跳触发)"""
        return self.devices.touch_last_seen(device_id, get_time())

    def list_user_devices(self, user_uuid: str) -> list[dict]:
        """获取用户名下所有活跃设备列表 (仅包含当前有有效会话的设备)"""
        # 使用联表查询确保只返回在线的设备，防止已下线的设备在列表中占位
        # 同时保留数据库中的 device 记录，以维持历史消息的元数据完整性
        query = """
            SELECT DISTINCT d.* FROM devices d
            JOIN sessions s ON d.device_id = s.device_id
            WHERE d.user_uuid = ?
        """
        cursor = self.sessions.conn.execute(query, (user_uuid,))
        return [dict(r) for r in cursor.fetchall()]

    def revoke_device(self, user_uuid: str, device_id: str) -> bool:
        """强制注销并下线特定设备 (仅使会话失效，保留设备记录及历史消息)"""
        device = self.devices.get_by_device_id(device_id)
        if not device or device["user_uuid"] != user_uuid:
            logger.warning(f"设备下线失败 | 设备 {device_id[:8]} 不属于用户 {user_uuid[:8]}")
            return False
            
        # 1. 内存清洗：踢出该设备关联的所有在线 Token
        with _SESSION_LOCK:
            cache_keys = list(_SESSION_CACHE.keys())
            kicked_count = 0
            for tk in cache_keys:
                if _SESSION_CACHE[tk].get("device_id") == device_id:
                    _SESSION_CACHE.pop(tk, None)
                    kicked_count += 1
                    
        # 2. 数据库级清理：仅删除 Session，使其 Token 失效
        # 故意保留 devices 表中的记录，以防止级联删除关联的 messages
        self.sessions.delete_by_device_id(device_id)
        
        logger.warning(f"设备已下线 | 用户 {user_uuid[:8]} 使得设备 {device_id[:8]} ({device['device_name']}) 的会话失效。清理了 {kicked_count} 个 Token。")
        return True

    def admin_update_quota(self, admin_uuid: str, target_uuid: str, storage_quota: int):
        """管理员：动态调整用户存储配额"""
        logger.info(f"审计 | 管理员 {admin_uuid[:8]} 修改用户 {target_uuid[:8]} 配额为 {storage_quota} Bytes")
        return self.users.update_quota(target_uuid, storage_quota)

    def admin_update_status(self, admin_uuid: str, target_uuid: str, is_active: bool):
        """管理员：启用或禁用用户"""
        if admin_uuid == target_uuid:
            raise ForbiddenError("Admin cannot disable themselves.")
        
        logger.info(f"审计 | 管理员 {admin_uuid[:8]} 设置用户 {target_uuid[:8]} 状态为 {'启用' if is_active else '禁用'}")
        
        # 如果是禁用操作，强制踢出所有在线会话
        if not is_active:
            with _SESSION_LOCK:
                cache_keys = list(_SESSION_CACHE.keys())
                for tk in cache_keys:
                    if _SESSION_CACHE[tk]["user_uuid"] == target_uuid:
                        _SESSION_CACHE.pop(tk, None)
                        self.sessions.delete_by_token(tk)
            logger.info(f"审计 | 用户 {target_uuid[:8]} 已被强制下线")
            
        return self.users.update_status(target_uuid, is_active)

    def admin_hard_delete_user(self, admin_uuid: str, target_uuid: str):
        """管理员：物理销毁用户。核心任务是核减物理文件引用计数，行删除依靠 DB 级联。"""
        if admin_uuid == target_uuid:
            raise LoginError("Admin cannot delete themselves.")
        
        user = self.users.get_by_uuid(target_uuid)
        if not user: return
        
        logger.warning(f"审计 | 管理员 {admin_uuid[:8]} 正在物理销毁用户: {user.account} ({target_uuid[:8]})")
        
        # 1. 物理引用计数精准核减 (关键：数据库级联删除无法自动减计数)
        # 获取该用户名下所有消息关联的所有附件哈希 (不使用 DISTINCT，因为多次引用需多次核减)
        cursor = self.users.conn.execute("""
            SELECT a.file_hash FROM attachments a
            JOIN messages m ON a.message_id = m.id
            WHERE m.sender_uuid = ?
        """, (target_uuid,))
        hashes = [r[0] for r in cursor.fetchall()]
        
        if hashes:
            for h in hashes:
                self.users.conn.execute(
                    "UPDATE file_info SET refer_count = refer_count - 1 WHERE full_hash = ?",
                    (h,)
                )
            logger.info(f"审计 | 已核减用户 {len(hashes)} 个物理文件引用计数")

        # 2. 内存清洗：踢出该用户的所有在线会话
        with _SESSION_LOCK:
            cache_keys = list(_SESSION_CACHE.keys())
            kicked_count = 0
            for tk in cache_keys:
                if _SESSION_CACHE[tk]["user_uuid"] == target_uuid:
                    _SESSION_CACHE.pop(tk, None)
                    kicked_count += 1
        
        # 3. 彻底删除用户记录 (依靠数据库 00_init_v2.sql 中的 ON DELETE CASCADE)
        self.users.delete_user(target_uuid)
        logger.success(f"审计 | 用户销毁完成。清理了 {kicked_count} 个活跃 Session。")

    def change_password(self, user_uuid: str, old_password: str, new_password: str):
        """用户自服务：修改密码"""
        user = self.users.get_by_uuid(user_uuid)
        if not user or not AuthManager.verify_password_hash(old_password, user.password_hash):
            logger.warning(f"密码修改失败 | 用户 {user_uuid[:8]} 旧密码验证不通过")
            raise LoginError("Old password incorrect")
        
        new_hash = AuthManager.get_password_hash(new_password)
        self.users.update_password_hash(user_uuid, new_hash)
        # 修改密码后注销所有 Token 是一种安全策略，但此处简单起见仅更新数据库
        logger.success(f"密码修改成功 | 用户 {user_uuid[:8]}")

    @staticmethod
    def clean_expired_sessions():
        """定时任务调用：清理内存中的过期会话"""
        now = get_time()
        # 安全处理：先获取键的快照，防止迭代时字典大小改变
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
