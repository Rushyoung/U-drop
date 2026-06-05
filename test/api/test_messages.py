import pytest

def test_message_with_multiple_attachments(client, auth_headers):
    """测试单条消息带多个附件的初始化与占位"""
    
    # 1. 创建带 2 个文件的消息
    files = [
        {"file_name": "image1.jpg", "total_size": 100, "sparse_hash": "sparse1", "mime_type": "image/jpeg"},
        {"file_name": "doc1.pdf", "total_size": 500, "sparse_hash": "sparse2", "mime_type": "application/pdf"}
    ]
    
    resp = client.post("/api/v1/messages", json={
        "content": "Multi-file test",
        "files": files
    }, headers=auth_headers)
    
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "accepted"
    assert len(data["upload_tasks"]) == 2
    
    message_id = data["message_id"]

    # 2. 拉取时间线，验证聚合显示 (幻影模式)
    timeline_resp = client.get("/api/v1/messages?mode=initial", headers=auth_headers)
    assert timeline_resp.status_code == 200
    
    timeline = timeline_resp.json()["data"]
    # 找到刚才那条消息
    msg = next(m for m in timeline if m["id"] == message_id)
    
    assert len(msg["pending_uploads"]) == 2
    assert len(msg["attachments"]) == 0
    assert msg["pending_uploads"][0]["file_name"] in ["image1.jpg", "doc1.pdf"]

def test_message_trash_and_restore(client, auth_headers):
    """测试回收站：删除、查看、恢复"""
    
    # 1. 发一条纯文本消息
    msg_resp = client.post("/api/v1/messages", json={"content": "Trash test"}, headers=auth_headers)
    message_id = msg_resp.json()["data"]["message_id"]
    
    # 2. 执行软删除
    del_resp = client.delete(f"/api/v1/messages/{message_id}", headers=auth_headers)
    assert del_resp.status_code == 200
    
    # 3. 时间线应该看不见了
    timeline = client.get("/api/v1/messages?mode=initial", headers=auth_headers).json()["data"]
    assert not any(m["id"] == message_id for m in timeline)
    
    # 4. 回收站应该能看见
    trash = client.get("/api/v1/messages/trash", headers=auth_headers).json()["data"]
    assert any(m["id"] == message_id for m in trash)
    
    # 5. 恢复消息
    restore_resp = client.post(f"/api/v1/messages/{message_id}/restore", headers=auth_headers)
    assert restore_resp.status_code == 200
    
    # 6. 时间线又看见了
    timeline_after = client.get("/api/v1/messages?mode=initial", headers=auth_headers).json()["data"]
    assert any(m["id"] == message_id for m in timeline_after)

def test_empty_trash(client, auth_headers):
    """测试清空回收站 (物理删除)"""
    
    # 1. 发送并删除
    msg_resp = client.post("/api/v1/messages", json={"content": "Hard delete test"}, headers=auth_headers)
    mid = msg_resp.json()["data"]["message_id"]
    client.delete(f"/api/v1/messages/{mid}", headers=auth_headers)
    
    # 2. 清空
    empty_resp = client.delete("/api/v1/messages/trash/empty", headers=auth_headers)
    assert empty_resp.status_code == 200
    
    # 3. 回收站也没了
    trash = client.get("/api/v1/messages/trash", headers=auth_headers).json()["data"]
    assert not any(m["id"] == mid for m in trash)
