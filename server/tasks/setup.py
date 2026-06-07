import asyncio
import importlib
import random
from pathlib import Path
from typing import Callable

from server.tasks.register import TASKS
from core.logger import logger


def _discover_tasks():
    """
    自动发现并加载当前目录下的任务模块。
    通过动态导入触发各模块中的 @register 装饰器。
    """
    task_dir = Path(__file__).parent
    for file_path in task_dir.glob("*.py"):
        module_name = file_path.stem
        if module_name in ["setup", "register", "__init__"]:
            continue

        try:
            import_path = f"server.tasks.{module_name}"
            importlib.import_module(import_path)
        except Exception as e:
            logger.error(f"Failed to auto-discover task '{module_name}': {e}")


async def _run_periodic_task(name: str, func: Callable, base_interval: int):
    """
    通用周期任务执行器
    :param name: 任务名称
    :param func: 任务函数
    :param base_interval: 基础执行间隔（秒）
    """
    jitter = random.randint(-5, 5)
    interval = base_interval + jitter

    logger.info(f"Task '{name}' registered with interval: {interval}s")

    try:
        while True:
            await asyncio.sleep(interval)
            interval = base_interval + random.randint(-5, 5)
            await asyncio.to_thread(func) if not asyncio.iscoroutinefunction(func) else await func()
    except asyncio.CancelledError:
        logger.info(f"Task '{name}' stopped.")
    except Exception as e:
        logger.error(f"Error in task '{name}': {e}")


class setup:
    def __init__(self):
        """
        初始化 setup 实例
        该实例在 server/main.py 的 lifespan 中被创建
        """
        _discover_tasks()

        self.tasks: list[asyncio.Task] = []
        for name, (func, interval) in TASKS.items():
            self.tasks.append(
                asyncio.create_task(_run_periodic_task(name, func, interval))
            )

    def stop(self):
        """
        停止所有后台定时任务
        该函数在 server/main.py 的 lifespan 中被调用
        """
        for task in self.tasks:
            task.cancel()
