import ctypes
import os
import asyncio


def calc_sparse_hash(filename):
    raise NotImplementedError

async def asy_calc_sparse_hash(filename):
    return await asyncio.to_thread(calc_sparse_hash, filename)

# [TODO] blake3算法需要调整，目前似乎不支持多线程并发处理单文件
def calc_full_hash(filename):
    raise NotImplementedError

async def asy_calc_calc_full_hash(filename):
    raise NotImplementedError



