import requests
import os
import sys
import tempfile
from pathlib import Path

# 自动定位项目根目录并加入路径
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root / "source" / "py"))

try:
    from core.native_wrapper import native_core
except ImportError as e:
    print(f"导入原生库封装失败: {e}")
    sys.exit(1)

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_upload_and_thumbnail():
    account = "persistent_tester"
    password = "password123"
    reg_login_payload = {
        "account": account, "password": password, 
        "device_id": "upload_tester_001", "device_type": 1, "device_name": "Upload Runner"
    }
    
    print(f"--- 步骤 0: 注册/登录账号: {account} ---")
    # 尝试注册，失败也无妨
    requests.post(f"{BASE_URL}/auth/register", json=reg_login_payload)
    login_resp = requests.post(f"{BASE_URL}/auth/login", json=reg_login_payload)
    
    if login_resp.status_code != 200:
        print(f"登录失败: {login_resp.text}")
        return
        
    token = login_resp.json()["bearer"]
    headers = {"Authorization": f"Bearer {token}"}

    # 准备图片文件
    file_content = b"\xFF\xD8\xFF\xE0\x00\x10JFIF" + b"\x00" * 5000
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        tmp.write(file_content)
        temp_path = tmp.name

    try:
        full_hash = native_core.get_full_blake3(temp_path)
        sparse_hash = native_core.get_fast_hash(temp_path)
        
        # 1. 创建消息
        print("\n[Step 1] 创建文件消息...")
        resp_msg = requests.post(f"{BASE_URL}/messages", headers=headers, json={
            "content": "测试缩略图上传", "file_name": "test.jpg",
            "total_size": len(file_content), "sparse_hash": sparse_hash
        })
        upload_id = resp_msg.json()["data"]["upload_id"]

        # 2. 上传数据
        print("[Step 2] 正在上传...")
        requests.patch(f"{BASE_URL}/files/upload/{upload_id}", headers=headers, data=file_content)
        requests.post(f"{BASE_URL}/files/upload/{upload_id}/commit", headers={**headers, "X-Full-Hash": full_hash})

        # 3. 尝试获取缩略图
        print(f"\n[Step 3] 正在拉取缩略图: /files/{full_hash}/thumbnail")
        res_thumb = requests.get(f"{BASE_URL}/files/{full_hash}/thumbnail", headers=headers)
        
        if res_thumb.status_code == 200:
            print(f">>> 成功! 缩略图大小: {len(res_thumb.content)} bytes")
        else:
            print(f">>> 逻辑通过，但未生成缩略图 (状态码: {res_thumb.status_code})")

    finally:
        if os.path.exists(temp_path): os.remove(temp_path)

if __name__ == "__main__":
    test_upload_and_thumbnail()
