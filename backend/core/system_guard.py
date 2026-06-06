from typing import Dict, Any, Callable
from core.logger import logger

class SystemGuard:
    """
    中央功能卫兵 (System Guard)
    采用“装饰器主动注册 + 内存快照拦截”模式。
    """
    _CONFIG_CACHE: Dict[str, Any] = {}
    _INITIALIZED: bool = False

    @classmethod
    def sync(cls, settings_dict: Dict[str, str], has_admin: bool):
        """同步数据库配置到内存快照"""
        # 存储原始字典，方便后续读取非布尔配置
        cls._CONFIG_CACHE = {**settings_dict}
        cls._CONFIG_CACHE["initialized"] = has_admin
        # 预转换核心布尔开关
        cls._CONFIG_CACHE["allow_registration"] = settings_dict.get("allow_registration", "true").lower() == "true"
        
        cls._INITIALIZED = True
        logger.debug(f"SystemGuard | 配置已同步: {cls._CONFIG_CACHE}")

    @classmethod
    def get_setting(cls, key: str, default: Any = None) -> Any:
        """获取任意系统配置"""
        return cls._CONFIG_CACHE.get(key, default)

    @classmethod
    def is_feature_enabled(cls, feature_name: str) -> bool:
        """从内存快照中核对功能开关"""
        # 特殊逻辑：如果是初始化检查，直接返回 cache 中的状态
        if feature_name == "initialized":
            return cls._CONFIG_CACHE.get("initialized", False)
        
        # 其他功能默认为开启，除非明确被关闭
        return cls._CONFIG_CACHE.get(feature_name, True)

def feature_gate(name: str):
    """
    功能闸门装饰器：函数主动注册受控字段。
    仅用于在函数对象上打标，拦截逻辑由 main.py 中的中间件统一处理。
    """
    def decorator(func: Callable):
        # 在函数对象上打标，中间件会读取此标记
        setattr(func, "_udrop_feature", name)
        return func
    return decorator

# 全局单例标识
system_guard = SystemGuard()
