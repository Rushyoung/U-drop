import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
from api.router import router
from core.exceptions import UdropException
from contextlib import asynccontextmanager
import traceback
import asyncio
import time
import os
from pathlib import Path

from db.bootstrap import initialize_database
from core.logger import setup_logger, logger
from dependencies import open_connection
from db.repositories.users import UserRepository
from db.repositories.messages import MessageRepository
from db.repositories.attachments import AttachmentRepository
from db.repositories.file_info import FileInfoRepository
from db.services.file_service import FileService
from db.services.auth_service import AuthService
from schemas.base import ResponseSchema
from core.config import settings
from core.system_guard import SystemGuard
from core.rate_limiter import RateLimitMiddleware

def _perform_gc_sync():
    """同步执行的清理逻辑，运行在独立线程中"""
    conn = open_connection()
    try:
        user_repo = UserRepository(conn)
        msg_repo = MessageRepository(conn)
        attach_repo = AttachmentRepository(conn)
        file_info_repo = FileInfoRepository(conn)
        
        # 1. 内存清理
        AuthService.clean_expired_sessions()

        # 2. 逻辑清理：过期消息处理与配额返还
        total_logic_cleaned = 0
        user_settings = user_repo.get_trash_settings_for_all()
        for user in user_settings:
            user_uuid = user['uuid']
            expire_days = user['trash_expire_days']
            expired_msgs = msg_repo.list_expired_for_user(user_uuid, expire_days)
            for msg_row in expired_msgs:
                mid = msg_row['id']
                attachs = attach_repo.list_by_message_id(mid)
                total_size_freed = sum([a['file_size'] for a in attachs])
                attach_repo.delete_by_message_id(mid)
                msg_repo.hard_delete_message(mid)
                user_repo.update_used_storage(user_uuid, -total_size_freed)
                total_logic_cleaned += 1
        
        # 3. 物理清理：孤儿文件及缩略图 (手动同步调用 FileService 核心逻辑)
        total_phys_cleaned = 0
        orphans = file_info_repo.list_orphans()
        for row in orphans:
            full_hash = row['full_hash']
            storage_path = row['storage_path']
            # 物理文件删除
            if storage_path.startswith("local://"):
                rel_path = storage_path.replace("local://", "")
                abs_path = settings.STORAGE_ROOT / rel_path
                if abs_path.exists():
                    try: os.remove(abs_path)
                    except: pass
            # 缩略图删除
            thumb_path = settings.THUMBNAIL_ROOT / f"{full_hash}.jpg"
            if thumb_path.exists():
                try: os.remove(thumb_path)
                except: pass
            file_info_repo.delete_file_info(full_hash)
            total_phys_cleaned += 1

        # 4. 临时文件清理与内存任务回收
        temp_dir = settings.STORAGE_ROOT / "temp"
        total_tmp_cleaned = 0
        
        # 先清理内存中的过期任务记录 (这会自动尝试清理对应的磁盘临时文件)
        from core.uploads_manager import uploads_manager
        uploads_manager.cleanup_old_tasks(86400)

        # 再兜底清理磁盘上可能的孤儿临时文件 (例如进程崩溃导致的遗留)
        if temp_dir.exists():
            now = time.time()
            for tmp_file in temp_dir.iterdir():
                if tmp_file.is_file() and (now - tmp_file.stat().st_mtime > 86400):
                    # 安全加固：校验是否仍有活跃任务关联
                    upload_id = tmp_file.name.replace(".tmp", "")
                    if not uploads_manager.get_task(upload_id):
                        try: 
                            os.remove(tmp_file)
                            total_tmp_cleaned += 1
                        except: pass
                    else:
                        logger.debug(f"GC | 跳过活跃任务关联的临时文件: {tmp_file.name}")

        conn.commit()
        return total_logic_cleaned, total_phys_cleaned, total_tmp_cleaned
    finally:
        conn.close()

async def background_gc_task():
    """自动化 GC 任务：每小时执行一次"""
    logger.info("后台清理协程已启动 [1h 周期]")
    while True:
        try:
            logger.info("执行例行磁盘与数据库清理 (GC)...")
            res = await run_in_threadpool(_perform_gc_sync)
            l_clean, p_clean, t_clean = res
            if l_clean > 0 or p_clean > 0 or t_clean > 0:
                logger.success(f"GC 清理完成：逻辑删除 {l_clean} 条，物理回收 {p_clean} 个，清理碎片 {t_clean} 个。")
        except Exception as e:
            logger.error(f"后台清理任务异常: {e}")
            logger.debug(traceback.format_exc())
        await asyncio.sleep(3600)

def ensure_directories():
    """确保项目运行所需的目录结构存在"""
    dirs = [
        settings.STORAGE_ROOT,
        settings.THUMBNAIL_ROOT,
        settings.STORAGE_ROOT / "temp",
        settings.PROJECT_ROOT / "logs"
    ]
    for d in dirs:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            logger.info(f"初始化 | 创建目录: {d}")

def bootstrap_system():
    """系统自举：检查是否需要通过环境变量自动创建管理员"""
    from db.repositories.users import UserRepository
    from db.repositories.system import SystemRepository
    from db.services.system_service import SystemService
    
    conn = open_connection()
    try:
        user_repo = UserRepository(conn)
        if not user_repo.has_admin():
            account = settings.ADMIN_ACCOUNT
            password = settings.ADMIN_PASSWORD
            if account and password:
                system_service = SystemService(SystemRepository(conn), user_repo)
                # 传入默认限流配置
                system_service.initialize_system(account, password, settings.ALLOW_REGISTRATION, auth_rate_limit=5)
                logger.success(f"自举成功 | 已通过环境变量创建管理员: {account}")
            else:
                logger.warning("系统尚未初始化，请通过 Web 向导完成设置或配置管理员环境变量。")
    finally:
        conn.close()

@asynccontextmanager
async def lifespan(app:FastAPI):
    setup_logger()
    ensure_directories()
    initialize_database()
    
    # 首次同步 SystemGuard 缓存
    conn = open_connection()
    try:
        from db.repositories.system import SystemRepository
        from db.repositories.users import UserRepository
        sys_repo = SystemRepository(conn)
        user_repo = UserRepository(conn)
        SystemGuard.sync(sys_repo.get_all_settings(), user_repo.has_admin())
    finally:
        conn.close()

    bootstrap_system() # 尝试环境变量自举
    gc_task = asyncio.create_task(background_gc_task())
    yield
    gc_task.cancel()

app = FastAPI(
    title="U-Drop Backend API",
    description="## U-Drop: 个人碎片内容管理系统",
    version="0.5.1",
    lifespan=lifespan
)

# 增加 CORS 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 个人云场景默认允许所有来源，生产环境可限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 增加认证频率限制
app.add_middleware(RateLimitMiddleware)

@app.middleware("http")
async def system_guard_middleware(request: Request, call_next):
    """
    中央功能卫兵中间件
    1. 强制拦截未初始化的系统（除白名单外）
    2. 拦截被 @feature_gate 标记且已禁用的功能
    """
    path = request.url.path
    
    # --- 1. 初始化强制拦截逻辑 ---
    # 非 API 路径 (SPA 页面、静态资源、健康检查等) 始终放行，让前端能加载并自行引导
    # 仅针对未初始化的系统拦截除 status/setup 以外的 API 请求
    if path.startswith("/api/v1"):
        whitelist = ["/api/v1/system/status", "/api/v1/system/setup"]
        if path not in whitelist:
            if not SystemGuard.is_feature_enabled("initialized"):
                return JSONResponse(
                    status_code=403,
                    content=ResponseSchema.fail("System not initialized.", 403).model_dump()
                )

    # --- 2. 动态功能开关拦截 (@feature_gate) ---
    # 尝试找到匹配的路由并检查装饰器标记
    for route in app.routes:
        if hasattr(route, "path_regex") and route.path_regex.match(path):
            endpoint = getattr(route, "endpoint", None)
            # 检查函数是否带有主动注册的标签
            if endpoint and hasattr(endpoint, "_udrop_feature"):
                feature_name = getattr(endpoint, "_udrop_feature")
                if not SystemGuard.is_feature_enabled(feature_name):
                    logger.warning(f"功能拦截 | 用户试图访问已禁用的功能: {feature_name} | 路径: {path}")
                    return JSONResponse(
                        status_code=403,
                        content=ResponseSchema.fail(f"Feature '{feature_name}' is disabled.", 403).model_dump()
                    )
            break

    return await call_next(request)

@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    ip = request.headers.get("X-Forwarded-For", request.client.host)
    if not request.url.path.startswith(("/docs", "/openapi.json", "/favicon.ico")):
        logger.info(f"REQ | IP: {ip: <15} | {request.method: <6} | {request.url.path}")
    response = await call_next(request)
    return response

@app.exception_handler(UdropException)
async def udrop_exception_handler(req: Request, exc: UdropException):
    # 增加日志：但不记录敏感 content
    logger.warning(f"业务异常: {exc.message} (Code: {exc.code}) | 路径: {req.url.path}")
    return JSONResponse(
        status_code=exc.code, 
        content=ResponseSchema.fail(exc.message, exc.code).model_dump()
    )

@app.exception_handler(FastAPIHTTPException)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(req: Request, exc: FastAPIHTTPException | StarletteHTTPException):
    """统一处理标准 HTTP 异常，防止被全局 Exception 处理器捕获为 500"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ResponseSchema.fail(exc.detail, exc.status_code).model_dump()
    )

@app.exception_handler(Exception)
async def global_exception_handler(req: Request, exc: Exception):
    # 安全加固：不将详细堆栈直接返回给客户端
    logger.exception(f"系统未捕获异常: {str(exc)} | 触发路径: {req.url.path}")
    return JSONResponse(
        status_code=500, 
        content=ResponseSchema.fail("Internal Server Error", 500).model_dump()
    )

app.include_router(router, prefix="/api/v1")

# --- 前端静态资源挂载与 Catch-All 网关 ---

# 1. 挂载特定的静态子目录
if settings.FRONTEND_DIST_DIR.exists():
    if (settings.FRONTEND_DIST_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=settings.FRONTEND_DIST_DIR / "assets"), name="assets")
    if (settings.FRONTEND_DIST_DIR / "static").exists():
        app.mount("/static", StaticFiles(directory=settings.FRONTEND_DIST_DIR / "static"), name="static")

@app.get("/health", tags=["System"])
async def health_check():
    """健康检查接口：返回系统基本存活状态"""
    return {"status": "ok", "timestamp": int(time.time()), "version": "0.5.1"}

@app.get("/{catchall:path}", tags=["System"])
async def serve_vue_app(catchall: str):
    """拦截所有非 API 请求，支持 Vue History 路由或静态资源"""
    # 1. 拦截 API 路由，兜底返回 404，防止 API 请求被当成页面返回
    if catchall.startswith(("api/", "docs", "openapi.json")):
        return JSONResponse(
            status_code=404, 
            content=ResponseSchema.fail("Not found", 404).model_dump()
        )
        
    # 2. 检查前端产物是否存在
    index_path = settings.FRONTEND_DIST_DIR / "index.html"
    if not settings.FRONTEND_DIST_DIR.exists() or not index_path.exists():
        return HTMLResponse("<h1>U-Drop 后端运行中，但前端未编译。</h1><p>请在 frontend/ 下执行 npm run build。</p>")
        
    # 3. 尝试匹配根目录下的静态资源文件 (如 /favicon.ico, /logo.png)
    file_path = settings.FRONTEND_DIST_DIR / catchall
    if catchall and file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
        
    # 4. 其他所有未知路由 (Vue Router 的前端路由)，统一返回 index.html
    return FileResponse(index_path)

if __name__ == '__main__':
    # 生产环境建议通过外部传参控制 reload
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
