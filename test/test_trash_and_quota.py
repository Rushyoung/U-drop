import requests
import time
import sys
from pathlib import Path

# 接入测试客户端
sys.path.append(str(Path(__file__).resolve().parent))
from client import UdropClient

def test_trash_and_quota():
    client = UdropClient()
    account = "quota_tester"
    password = "password123"
    
    print(f"--- 1. 登录并查看初始配额 ---")
    client.register(account, password, "quota_device")
    client.login(account, password, "quota_device")
    
    me_res = requests.get(f"{client.base_url}/auth/me", headers=client.headers).json()
    used = me_res['data']['used_storage']
    quota = me_res['data']['storage_quota']
    print(f"当前用量: {used}/{quota} Bytes")

    # 2. 发送消息并删除 (进入回收站)
    print(f"\n--- 2. 发送消息并执行软删除 ---")
    msg_res = client.create_message(content="即将被回收的消息")
    msg_id = msg_res.json()['data']['message_id']
    
    # 确认消息在时间线
    timeline = client.get_messages().json()['data']
    print(f"消息 {msg_id} 是否在时间线: {any(m['id'] == msg_id for m in timeline)}")
    
    # 执行删除
    del_res = requests.delete(f"{client.base_url}/messages/{msg_id}", headers=client.headers)
    print(f"删除结果: {del_res.json()['message']}")
    
    # 3. 检查回收站
    print(f"\n--- 3. 检查回收站列表 ---")
    trash_res = requests.get(f"{client.base_url}/messages/trash", headers=client.headers).json()
    trash_ids = [m['id'] for m in trash_res['data']]
    print(f"回收站内的消息 IDs: {trash_ids}")
    
    # 4. 恢复消息
    print(f"\n--- 4. 测试恢复功能 ---")
    restore_res = requests.post(f"{client.base_url}/messages/{msg_id}/restore", headers=client.headers)
    print(f"恢复结果: {restore_res.json()['message']}")
    
    # 再次确认时间线
    timeline_after = client.get_messages().json()['data']
    print(f"消息 {msg_id} 是否已回到时间线: {any(m['id'] == msg_id for m in timeline_after)}")

    # 5. 测试清空回收站 (物理清理)
    print(f"\n--- 5. 测试一键清空回收站 ---")
    # 先再删掉它
    requests.delete(f"{client.base_url}/messages/{msg_id}", headers=client.headers)
    empty_res = requests.delete(f"{client.base_url}/messages/trash/empty", headers=client.headers)
    print(f"清空结果: {empty_res.json()['message']}")

if __name__ == "__main__":
    test_trash_and_quota()
