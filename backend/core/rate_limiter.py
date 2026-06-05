import time
from typing import Dict, Tuple
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from core.logger import logger
from core.system_guard import SystemGuard
from schemas.base import ResponseSchema

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    轻量级速率限制中间件
    针对 /auth/login 和 /auth/register 接口进行 IP 级别的频率限制。
    配置从 SystemGuard 动态读取。
    """
    def __init__(self, app):
        super().__init__(app)
        # 内存存储：{ ip: (次数, 最后请求时间) }
        self.history: Dict[str, Tuple[int, float]] = {}
        self.request_count = 0
        self.MAX_HISTORY_SIZE = 10000 # 最大记录 IP 数

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # 保护路径：登录、注册、以及分享验证/下载接口
        is_auth_path = path in ["/api/v1/auth/login", "/api/v1/auth/register"]
        is_share_path = path.startswith("/api/v1/share/")

        # 定期清理过期记录
        self.request_count += 1
        if self.request_count >= 100:
            self.request_count = 0
            now = time.time()
            # 清理 1 分钟前未活动的记录
            expired_ips = [ip for ip, (_, last_time) in self.history.items() if now - last_time > 60]
            for ip in expired_ips:
                self.history.pop(ip, None)
            
            # 如果清理后依然超限，强制弹出最早的记录 (FIFO)
            while len(self.history) > self.MAX_HISTORY_SIZE:
                try:
                    oldest_ip = next(iter(self.history))
                    self.history.pop(oldest_ip)
                except StopIteration: break

        if is_auth_path or is_share_path:
            # 从 SystemGuard 获取配置
            # 对于分享接口，我们可以共用认证限流配置，或者未来拆分
            limit = int(SystemGuard.get_setting("auth_rate_limit", "5"))

            
            if limit > 0:
                ip = request.headers.get("X-Forwarded-For", request.client.host)
                now = time.time()
                
                count, last_time = self.history.get(ip, (0, 0))
                
                # 滑动窗口简化版：每分钟重置
                if now - last_time > 60:
                    count = 1
                else:
                    count += 1
                
                self.history[ip] = (count, now)
                
                if count > limit:
                    logger.warning(f"频率拦截 | IP {ip} 触发认证限制 (>{limit}次/分)")
                    return JSONResponse(
                        status_code=429,
                        content=ResponseSchema.fail("Too many requests. Please try again in a minute.", 429).model_dump()
                    )

        return await call_next(request)
