from typing import Callable, Dict

TASKS: Dict[str, tuple[Callable, int]] = {}


def register(name: str, interval: int = 3600):
    """
    任务注册装饰器
    :param name: 任务唯一标识名称
    :param interval: 任务执行间隔（秒），默认 3600 秒（1 小时）
    """

    def decorator(func: Callable):
        TASKS[name] = (func, interval)
        return func

    return decorator
