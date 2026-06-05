import sys
import os
from pathlib import Path

# 将 source/py 加入路径
sys.path.append(str(Path(__file__).resolve().parents[1] / "source" / "py"))

from core.native_wrapper import native_core
from core.config import settings

def test_native():
    print("--- 开始原生库功能测试 ---")
    
    # 1. 准备测试文件
    test_file = Path(__file__).resolve().parent / "test.png"
    if not test_file.exists():
        print(f"❌ 找不到测试文件: {test_file}")
        return

    # 2. 测试全量 BLAKE3 哈希
    print(f"\n[测试 1] 计算全量 BLAKE3...")
    hash_val = native_core.get_full_blake3(str(test_file))
    if hash_val:
        print(f"✅ BLAKE3: {hash_val}")
    else:
        print("❌ BLAKE3 计算失败")

    # 3. 测试快速哈希 (MD5)
    print(f"\n[测试 2] 计算快速 MD5 (头中尾)...")
    fast_hash = native_core.get_fast_hash(str(test_file))
    if fast_hash:
        print(f"✅ Fast MD5: {fast_hash}")
    else:
        print("❌ Fast MD5 计算失败")

    # 4. 测试缩略图生成
    print(f"\n[测试 3] 生成缩略图...")
    out_thumb = Path(__file__).resolve().parent / "test_out.jpg"
    success = native_core.make_thumbnail(str(test_file), str(out_thumb))
    if success:
        print(f"✅ 缩略图生成成功: {out_thumb}")
    else:
        print("❌ 缩略图生成失败")

if __name__ == "__main__":
    # 提醒用户先编译
    lib_file = settings.LIB_DIR / "thumbnail.so"
    if not lib_file.exists():
        print(f"⚠️ 警告: 找不到 {lib_file}，请先运行 bash compile.sh")
    
    test_native()
