import ctypes
import os
import sys
from pathlib import Path
from core.logger import logger

class NativeCore:
    def __init__(self):
        self.lib = None
        self._load_library()

    def _load_library(self):
        # 确定库文件路径
        project_root = Path(__file__).resolve().parents[2]
        if sys.platform == "win32":
            lib_path = project_root / "lib" / "thumbnail.dll"
        else:
            lib_path = project_root / "lib" / "thumbnail.so"

        if not lib_path.exists():
            logger.error(f"原生库文件不存在: {lib_path}")
            return

        try:
            self.lib = ctypes.CDLL(str(lib_path))
            
            # 1. 稀疏 MD5 绑定
            if hasattr(self.lib, 'CalculateFastFileMD5'):
                self.lib.CalculateFastFileMD5.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
                self.lib.CalculateFastFileMD5.restype = ctypes.c_int

            # 2. 官方标准 BLAKE3 绑定 (支持 4.7GB+)
            if hasattr(self.lib, 'CalculateFileBLAKE3'):
                self.lib.CalculateFileBLAKE3.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
                self.lib.CalculateFileBLAKE3.restype = ctypes.c_int

            # 3. 缩略图生成
            if hasattr(self.lib, 'make_thumbnail'):
                self.lib.make_thumbnail.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
                self.lib.make_thumbnail.restype = ctypes.c_bool

            logger.info("✅ 成功加载原生核心库 (v0.5.1)")
        except Exception as e:
            logger.error(f"加载原生库失败: {e}")

    def get_sparse_md5(self, file_path: str) -> str:
        """获取文件稀疏哈希 (头中尾MD5)"""
        if not self.lib: return ""
        res_buf = ctypes.create_string_buffer(33)
        try:
            res = self.lib.CalculateFastFileMD5(file_path.encode('utf-8'), res_buf)
            return res_buf.value.decode('utf-8') if res == 0 else ""
        except Exception as e:
            logger.error(f"稀疏哈希计算异常: {e}")
            return ""

    def get_full_blake3(self, file_path: str) -> str:
        """
        获取文件标准 BLAKE3 哈希 (64位十六进制)
        采用官方实现，支持 4.7GB+ 大文件及 SIMD 加速
        """
        if not self.lib: return ""
        # BLAKE3-256 hex 长度为 64，+1 为 null 终止符
        res_buf = ctypes.create_string_buffer(65)
        try:
            res = self.lib.CalculateFileBLAKE3(file_path.encode('utf-8'), res_buf)
            if res == 0:
                return res_buf.value.decode('utf-8')
            else:
                logger.warning(f"BLAKE3 计算返回错误码: {res} | 文件: {file_path}")
                return ""
        except Exception as e:
            logger.error(f"BLAKE3 计算异常: {e}")
            return ""

    def make_thumbnail(self, src_path: str, dst_path: str) -> bool:
        """调用 C++ 核心生成缩略图"""
        if not self.lib: return False
        try:
            return self.lib.make_thumbnail(src_path.encode('utf-8'), dst_path.encode('utf-8'))
        except Exception as e:
            logger.error(f"缩略图生成异常: {e}")
            return False

# 全局单例
native_core = NativeCore()
