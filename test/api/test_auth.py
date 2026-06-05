import time
import pytest

def test_registration_flow(client):
    """测试基本注册流程"""
    account = "new_user"
    password = "password123"
    
    # 1. 首次注册
    resp = client.post("/api/v1/auth/register", json={
        "account": account,
        "password": password,
        "device_id": "dev_001",
        "device_type": 0
    })
    assert resp.status_code == 200
    assert "bearer" in resp.json()
    
    # 2. 重复注册
    resp_dup = client.post("/api/v1/auth/register", json={
        "account": account,
        "password": password,
        "device_id": "dev_002",
        "device_type": 0
    })
    assert resp_dup.status_code == 409
    assert "已经存在" in resp_dup.json()["message"]

def test_login_and_single_use(client):
    """测试用后即焚 Token 机制"""
    account = "single_use_user"
    password = "password123"
    
    # 注册
    client.post("/api/v1/auth/register", json={
        "account": account, "password": password, "device_id": "dev_001", "device_type": 0
    })
    
    # 1. 以 single_use=True 登录
    resp = client.post("/api/v1/auth/login", json={
        "account": account,
        "password": password,
        "device_id": "dev_001",
        "device_type": 0,
        "single_use": True
    })
    token = resp.json()["bearer"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. 第一次请求 (获取用户信息) -> 应该成功并触发销毁
    res1 = client.get("/api/v1/auth/me", headers=headers)
    assert res1.status_code == 200
    
    # 3. 第二次请求 -> 应该失败 (401)
    res2 = client.get("/api/v1/auth/me", headers=headers)
    assert res2.status_code == 401

def test_dynamic_expiration(client):
    """测试动态生存期 Token"""
    account = "exp_user"
    password = "password123"
    
    client.post("/api/v1/auth/register", json={
        "account": account, "password": password, "device_id": "dev_001", "device_type": 0
    })
    
    # 1. 登录并设置有效期为 2 秒
    resp = client.post("/api/v1/auth/login", json={
        "account": account,
        "password": password,
        "device_id": "dev_001",
        "device_type": 0,
        "expire_in": 2
    })
    token = resp.json()["bearer"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. 立即请求 -> 成功
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    
    # 3. 等待 3 秒
    print("等待 Token 过期...")
    time.sleep(3)
    
    # 4. 再次请求 -> 失败
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
