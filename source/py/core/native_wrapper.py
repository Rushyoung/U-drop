import ctypes
import platform
import logging
from core.config import settings

logger = logging.getLogger("udrop.native")

class NativeCore:
    def __init__(self):
        system = platform.system()
        ext = ".dll" if system == "Windows" else ".so"
        lib_path = settings.LIB_DIR / f"thumbnail{ext}"
        
        try:
            self.lib = ctypes.CDLL(str(lib_path))
            
            # --- 1. 缩略图函数声明 ---
            # int thumbnail(const char* src, const char* dst, int w, int h)
            if hasattr(self.lib, 'thumbnail'):
                self.lib.thumbnail.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
                self.lib.thumbnail.restype = ctypes.c_int
            
            # --- 2. 哈希函数声明 ---
            # int CalculateFileMD5(const char *filePath, char *md5Result)
            if hasattr(self.lib, 'CalculateFileMD5'):
                self.lib.CalculateFileMD5.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
                self.lib.CalculateFileMD5.restype = ctypes.c_int
            
            # int CalculateFastFileMD5(const char *filePath, char *md5Result)
            if hasattr(self.lib, 'CalculateFastFileMD5'):
                self.lib.CalculateFastFileMD5.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
                self.lib.CalculateFastFileMD5.restype = ctypes.c_int
                
            # int CalculateFileBLAKE3(const char *filePath, char *hexResult)
            if hasattr(self.lib, 'CalculateFileBLAKE3'):
                self.lib.CalculateFileBLAKE3.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
                self.lib.CalculateFileBLAKE3.restype = ctypes.c_int

            logger.info(f"成功加载原生核心库: {lib_path}")
        except Exception as e:
            logger.error(f"加载原生库失败: {lib_path}, 错误: {e}")
            self.lib = None

    def make_thumbnail(self, src: str, dst: str, width: int = 512, height: int = 512) -> bool:
        """调用 C++ 生成缩略图"""
        if not self._check_lib(): return False
        try:
            settings.THUMBNAIL_ROOT.mkdir(parents=True, exist_ok=True)
            res = self.lib.thumbnail(src.encode('utf-8'), dst.encode('utf-8'), width, height)
            return res == 0
        except Exception as e:
            logger.error(f"生成缩略图异常: {e}")
            return False

    def get_fast_hash(self, file_path: str) -> str:
        """获取文件快速哈希（头中尾MD5）"""
        if not self._check_lib(): return ""
        # 准备一个 33 字节的缓冲区用于接收 32 位十六进制字符串 + \0
        res_buf = ctypes.create_string_buffer(33)
        try:
            res = self.lib.CalculateFastFileMD5(file_path.encode('utf-8'), res_buf)
            return res_buf.value.decode('utf-8') if res == 0 else ""
        except Exception as e:
            logger.error(f"计算快速哈希异常: {e}")
            return ""

    def get_full_blake3(self, file_path: str) -> str:
        """获取文件全量 BLAKE3 哈希 (64位十六进制)"""
        if not self._check_lib(): return ""
        # 准备一个 65 字节的缓冲区用于接收 64 位十六进制字符串 + \0
        res_buf = ctypes.create_string_buffer(65)
        try:
            res = self.lib.CalculateFileBLAKE3(file_path.encode('utf-8'), res_buf)
            return res_buf.value.decode('utf-8') if res == 0 else ""
        except Exception as e:
            logger.error(f"计算 BLAKE3 异常: {e}")
            return ""

    def _check_lib(self):
        if not self.lib:
            logger.warning("原生库未加载")
            return False
        return True

# 单例模式
native_core = NativeCore()
