import ctypes
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LIB_PATH = BASE_DIR/"lib"
lib = ctypes.CDLL(LIB_PATH/"thumbnail.dll")

lib.thumbnail.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
lib.thumbnail.restype = ctypes.c_int


source_path = str(BASE_DIR/"test"/"test.png").encode('utf-8')
dest_path = str(BASE_DIR/"test"/"out1.jpg").encode('utf-8')
print(source_path)
result = lib.thumbnail(source_path, dest_path, 512, 512)
print(result)

