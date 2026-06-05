from client import UdropClient
import tempfile
import os
import sys
from pathlib import Path

# 引入原生库
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root / "source" / "py"))
from core.native_wrapper import native_core

def run_upload_tests():
    client = UdropClient()
    acc = "persistent_tester"
    # 使用与其它脚本一致的 device_id 确保 device_name 一致
    client.login(acc, "password123", "fixed_device_001")

    # 1. 寻找 test/test.png 文件
    test_file_path = Path(__file__).resolve().parent / "test.png"
    if not test_file_path.exists():
        print(f"错误: 未找到测试文件 {test_file_path}")
        return

    print(f"\n--- 正在测试文件: {test_file_path.name} ---")
    with open(test_file_path, "rb") as f:
        content = f.read()

    full_hash = native_core.get_full_blake3(str(test_file_path))
    sparse_hash = native_core.get_fast_hash(str(test_file_path))

    # 2. 创建文件消息
    res_msg = client.create_message(
        content=f"Upload Test - {test_file_path.name}",
        file_name=test_file_path.name,
        total_size=len(content),
        sparse_hash=sparse_hash
    )
    
    msg_data = res_msg.json().get("data", {})
    upload_id = msg_data.get("upload_id")
    if not upload_id:
        print("!!! 消息创建失败或未返回 upload_id")
        return

    # 3. PATCH 上传 (模拟带劫持的流式上传)
    print("\n>>> 正在执行 PATCH 上传 (带 X-Full-Hash 劫持测试)...")
    res_patch = client.upload_patch(upload_id, content, full_hash=full_hash)
    
    patch_data = res_patch.json().get("data", {})
    
    # --- 【关键逻辑：恰当处理闪传成功】 ---
    if patch_data.get("status") == "deduplicated":
        print("\n[SUCCESS] 检测到秒传命中 (Deduplicated)!")
        print(f"服务器已存在该文件 ({full_hash[:16]}...)，上传流程已自动中断。")
        print("根据业务逻辑，无需执行 Commit，任务已由服务端自动闭环。")
    else:
        # 4. 如果没有命中秒传，则必须执行 Commit 校验
        print("\n>>> 未命中秒传，正在执行最终 Commit 校验...")
        res_commit = client.commit_upload(upload_id, full_hash)
        if res_commit.status_code == 200:
            print("[SUCCESS] 文件上传并校验成功！")
        else:
            print(f"[FAILED] Commit 校验失败: {res_commit.text}")

    # 5. 最后验证缩略图和下载
    print(f"\n>>> 验证缩略图获取...")
    client.get_thumbnail(full_hash)

    print(f"\n>>> 验证文件下载...")
    res_dl, dl_name = client.download_file(full_hash)
    if res_dl.status_code == 200:
        if dl_name == test_file_path.name and len(res_dl.content) == len(content):
            print(f"[SUCCESS] 下载验证通过! 文件名一致且大小匹配。")
        else:
            print(f"[WARNING] 下载的文件校验不完全一致。")
    else:
        print(f"[FAILED] 下载测试失败。")

if __name__ == "__main__":
    run_upload_tests()
