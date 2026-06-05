import os
import sys
import pytest
import sqlite3
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

# 1. 确保项目源码路径
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root / "source" / "py"))

from main import app
from dependencies import get_db, get_file_service

# --- 数据库隔离 ---
_test_conn = None
def get_test_db_conn():
    global _test_conn
    if _test_conn is None:
        _test_conn = sqlite3.connect(":memory:", check_same_thread=False)
        _test_conn.row_factory = sqlite3.Row
        init_sql_path = project_root / "source" / "sql" / "00_init_v2.sql"
        with open(init_sql_path, "r", encoding="utf-8") as f:
            _test_conn.executescript(f.read())
        _test_conn.commit()
    return _test_conn

def override_get_db():
    conn = get_test_db_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise

# --- 全量 Mock 逻辑 ---

@pytest.fixture(scope="session", autouse=True)
def mock_native_core():
    """全局 Mock NativeCore，防止其在测试期间访问磁盘"""
    with patch("api.v1.files.native_core") as mock:
        # 让哈希计算永远成功返回它收到的那个预期值 (或者固定值)
        # 在测试中，我们可以通过 Mock 改变行为
        mock.get_full_blake3.return_value = "fake_blake3_hash_123"
        yield mock

def override_get_file_service():
    """提供一个完全不读磁盘的 FileService"""
    from db.repositories.file_info import FileInfoRepository
    repo = FileInfoRepository(get_test_db_conn())
    from db.services.file_service import FileService
    mock_service = FileService(repo)
    
    # 模拟路径解析
    async def mock_get_path(full_hash):
        p = MagicMock(spec=Path)
        p.exists.return_value = True
        return p, "mock_file.txt"
    
    # 模拟物理落盘
    async def mock_finalize(temp_path, full_hash, sparse_hash, mime_type):
        return f"local://mock/{full_hash}"

    mock_service.get_physical_path_and_name = mock_get_path
    mock_service.finalize_upload = mock_finalize
    return mock_service

# 注入 Overrides
app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_file_service] = override_get_file_service

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    yield
    if _test_conn: _test_conn.close()

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def auth_headers(client):
    account = "test_auto_user"
    client.post("/api/v1/auth/register", json={
        "account": account, "password": "password123", "device_id": "test_device_fixture", "device_type": 0
    })
    resp = client.post("/api/v1/auth/login", json={
        "account": account, "password": "password123", "device_id": "test_device_fixture", "device_type": 0
    })
    token = resp.json()["bearer"]
    return {"Authorization": f"Bearer {token}"}
