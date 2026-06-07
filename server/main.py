import time
from contextlib import asynccontextmanager

import uvicorn
from api.router import router
from core.config import settings
from core.exceptions import UdropException
from core.logger import logger, setup_logger
from core.rate_limiter import RateLimitMiddleware
from core.system_guard import SystemGuard
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from schemas.base import ResponseSchema
from starlette.exceptions import HTTPException as StarletteHTTPException

from server.database.setup import setup as database_setup
from server.tasks.setup import setup as task_setup


def ensure_directories():
    dirs = [
        settings.STORAGE_ROOT,
        settings.THUMBNAIL_ROOT,
        settings.STORAGE_ROOT / "temp",
        settings.PROJECT_ROOT / "logs",
    ]
    for d in dirs:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            logger.info(f"初始化 | 创建目录: {d}")


def bootstrap_system():
    from server.database.services.system import SystemService

    system_service = SystemService()
    if not system_service.has_admin():
        account = settings.ADMIN_ACCOUNT
        password = settings.ADMIN_PASSWORD
        if account and password:
            system_service.initialize_system(
                account, password, settings.ALLOW_REGISTRATION, auth_rate_limit=5
            )
            logger.success(f"自举成功 | 已通过环境变量创建管理员: {account}")
        else:
            logger.warning(
                "系统尚未初始化，请通过 Web 向导完成设置或配置管理员环境变量。"
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logger()
    ensure_directories()
    database_setup()

    from server.database.services.system import SystemService

    system_service = SystemService()
    SystemGuard.sync(system_service.get_all_settings_dict(), system_service.has_admin())

    bootstrap_system()

    task_manager = task_setup()
    yield
    task_manager.stop()


app = FastAPI(
    title="U-Drop Backend API",
    description="## U-Drop: 个人碎片内容管理系统",
    version="0.5.1",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)


@app.middleware("http")
async def system_guard_middleware(request: Request, call_next):
    path = request.url.path

    if path.startswith("/api/v1"):
        whitelist = ["/api/v1/system/status", "/api/v1/system/setup"]
        if path not in whitelist:
            if not SystemGuard.is_feature_enabled("initialized"):
                return JSONResponse(
                    status_code=403,
                    content=ResponseSchema.fail(
                        "System not initialized.", 403
                    ).model_dump(),
                )

    for route in app.routes:
        if hasattr(route, "path_regex") and route.path_regex.match(path):
            endpoint = getattr(route, "endpoint", None)
            if endpoint and hasattr(endpoint, "_udrop_feature"):
                feature_name = getattr(endpoint, "_udrop_feature")
                if not SystemGuard.is_feature_enabled(feature_name):
                    logger.warning(
                        f"功能拦截 | 用户试图访问已禁用的功能: {feature_name} | 路径: {path}"
                    )
                    return JSONResponse(
                        status_code=403,
                        content=ResponseSchema.fail(
                            f"Feature '{feature_name}' is disabled.", 403
                        ).model_dump(),
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
    logger.warning(f"业务异常: {exc.message} (Code: {exc.code}) | 路径: {req.url.path}")
    return JSONResponse(
        status_code=exc.code,
        content=ResponseSchema.fail(exc.message, exc.code).model_dump(),
    )


@app.exception_handler(FastAPIHTTPException)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    req: Request, exc: FastAPIHTTPException | StarletteHTTPException
):
    return JSONResponse(
        status_code=exc.status_code,
        content=ResponseSchema.fail(exc.detail, exc.status_code).model_dump(),
    )


@app.exception_handler(Exception)
async def global_exception_handler(req: Request, exc: Exception):
    logger.exception(f"系统未捕获异常: {str(exc)} | 触发路径: {req.url.path}")
    return JSONResponse(
        status_code=500,
        content=ResponseSchema.fail("Internal Server Error", 500).model_dump(),
    )


app.include_router(router, prefix="/api/v1")

if settings.FRONTEND_DIST_DIR.exists():
    if (settings.FRONTEND_DIST_DIR / "assets").exists():
        app.mount(
            "/assets",
            StaticFiles(directory=settings.FRONTEND_DIST_DIR / "assets"),
            name="assets",
        )
    if (settings.FRONTEND_DIST_DIR / "static").exists():
        app.mount(
            "/static",
            StaticFiles(directory=settings.FRONTEND_DIST_DIR / "static"),
            name="static",
        )


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "timestamp": int(time.time()), "version": "0.5.1"}


@app.get("/{catchall:path}", tags=["System"])
async def serve_vue_app(catchall: str):
    if catchall.startswith(("api/", "docs", "openapi.json")):
        return JSONResponse(
            status_code=404, content=ResponseSchema.fail("Not found", 404).model_dump()
        )

    index_path = settings.FRONTEND_DIST_DIR / "index.html"
    if not settings.FRONTEND_DIST_DIR.exists() or not index_path.exists():
        return HTMLResponse(
            "<h1>U-Drop 后端运行中，但前端未编译。</h1><p>请在 frontend/ 下执行 npm run build。</p>"
        )

    file_path = settings.FRONTEND_DIST_DIR / catchall
    if catchall and file_path.exists() and file_path.is_file():
        return FileResponse(file_path)

    return FileResponse(index_path)


if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)
