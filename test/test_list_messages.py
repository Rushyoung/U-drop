import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000/api/v1"

def format_msg(msg):
    line1 = f"ID: {msg['id']:<4} | Type: {msg['type']} | Device: {msg['device_name']} ({msg['device_type']})"
    line2 = f"Content: {msg['content']}"
    output = f"{line1}\n{line2}"
    if msg['file_info']:
        fi = msg['file_info']
        output += f"\n[Attachment] {fi['file_name']} ({fi['file_size']} bytes) | Hash: {fi['full_hash'][:16]}..."
    if msg['tags']:
        output += f"\nTags: {', '.join(msg['tags'])}"
    return output

def test_anchor_display():
    account = "persistent_tester"
    password = "password123"
    reg_login_payload = {
        "account": account, "password": password, 
        "device_id": "list_tester_001", "device_type": 0, "device_name": "List Viewer"
    }

    print(f"--- 步骤 0: 注册/登录账号: {account} ---")
    requests.post(f"{BASE_URL}/auth/register", json=reg_login_payload)
    login_resp = requests.post(f"{BASE_URL}/auth/login", json=reg_login_payload)
    
    if login_resp.status_code != 200:
        print(f"登录失败: {login_resp.text}")
        return
        
    token = login_resp.json()["bearer"]
    headers = {"Authorization": f"Bearer {token}"}

    print("\n" + "="*60)
    print(f"{'MESSAGE TIMELINE AUDIT':^60}")
    print("="*60)

    # 1. Initial
    print(f"\n>>> MODE: initial (latest 3 messages)")
    res = requests.get(f"{BASE_URL}/messages?mode=initial&limit=3", headers=headers)
    data = res.json()["data"]
    for m in data: print(f"{'-'*60}\n{format_msg(m)}")
    
    if not data: return

    # 2. Before
    oldest_id = data[-1]["id"]
    print(f"\n>>> MODE: before (anchor_id={oldest_id})")
    data_before = requests.get(f"{BASE_URL}/messages?mode=before&anchor_id={oldest_id}&limit=2", headers=headers).json()["data"]
    if data_before:
        for m in data_before: print(f"{'-'*60}\n{format_msg(m)}")
    else:
        print("   (No more older messages)")

    # 3. After
    newest_id = data[0]["id"]
    requests.post(f"{BASE_URL}/messages", headers=headers, json={"content": f"New update at {time.strftime('%H:%M:%S')}"})
    print(f"\n>>> MODE: after (anchor_id={newest_id})")
    data_after = requests.get(f"{BASE_URL}/messages?mode=after&anchor_id={newest_id}&limit=5", headers=headers).json()["data"]
    for m in data_after: print(f"{'-'*60}\n{format_msg(m)}")

    print("\n" + "="*60)

if __name__ == "__main__":
    test_anchor_display()
