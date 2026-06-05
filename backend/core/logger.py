import sys
import os
from pathlib import Path
from loguru import logger
from core.config import settings

# 确定日志存储目录 (在项目根目录下的 logs 文件夹)
LOG_DIR = settings.PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

def setup_logger():
    """
    初始化 Loguru 日志系统
    - 移除默认处理器
    - 添加控制台输出 (带颜色，DEBUG级别)
    - 添加应用全量日志 (INFO级别，按天滚动，保留30天)
    - 添加错误专用日志 (ERROR级别)
    """
    
    # 1. 移除 Loguru 默认的处理器 (避免重复打印)
    logger.remove()

    # 2. 定义统一的日志格式
    # <green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>
    LOG_FORMAT = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )

    # 3. 配置控制台处理器 (尊重配置等级)
    logger.add(sys.stdout, format=LOG_FORMAT, level=settings.LOG_LEVEL, colorize=True)

    # 4. 配置应用日志文件 (按天轮转, 压缩旧日志)
    logger.add(
        LOG_DIR / "app.log",
        format=LOG_FORMAT,
        level="INFO",
        rotation="00:00", # 每天零点分割
        retention="30 days", # 保留30天
        compression="zip", # 旧日志自动压缩
        encoding="utf-8",
        enqueue=True # 异步写入，不阻塞主线程
    )

    # 5. 配置错误日志文件 (仅记录错误，方便排查)
    logger.add(
        LOG_DIR / "error.log",
        format=LOG_FORMAT,
        level="ERROR",
        rotation="10 MB", # 错误日志按大小分割
        retention="3 months",
        encoding="utf-8",
        backtrace=False, # 安全加固：不记录过于详尽的堆栈
        diagnose=False,  # 安全加固：不泄露变量详情内容
        enqueue=True
    )

    logger.info("U-Drop 日志系统初始化完成。")

# 导出 logger 供全项目使用
__all__ = ["logger"]
