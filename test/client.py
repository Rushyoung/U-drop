import requests
import json
import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root / "source" / "py"))

class UdropClient:
    def __init__(self, base_url="http://127.0.0.1:8000/api/v1"):
        self.base_url = base_url
        self.token = None
        self.headers = {}

    def _print_res(self, res):
        print(f"<<< [{res.status_code}]")
        try:
            print(json.dumps(res.json(), indent=2, ensure_ascii=False))
        except:
            print(res.text)

    def register(self, account, password, device_id, device_type=0, device_name="TestDevice"):
        url = f"{self.base_url}/auth/register"
        payload = {
            "account": account, "password": password,
            "device_id": device_id, "device_type": device_type,
            "device_name": device_name
        }
        print(f"\n>>> [POST] Register: {account}")
        res = requests.post(url, json=payload)
        self._print_res(res)
        return res

    def login(self, account, password, device_id, device_type=0):
        url = f"{self.base_url}/auth/login"
        payload = {
            "account": account, "password": password,
            "device_id": device_id, "device_type": device_type
        }
        print(f"\n>>> [POST] Login: {account}")
        res = requests.post(url, json=payload)
        self._print_res(res)
        if res.status_code == 200:
            self.token = res.json().get("bearer")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        return res

    def create_message(self, content=None, file_name=None, total_size=0, sparse_hash=None, tags=None):
        url = f"{self.base_url}/messages"
        payload = {
            "content": content, "file_name": file_name,
            "total_size": total_size, "sparse_hash": sparse_hash,
            "tags": tags or []
        }
        print(f"\n>>> [POST] Create Message")
        res = requests.post(url, json=payload, headers=self.headers)
        self._print_res(res)
        return res

    def upload_patch(self, upload_id, data, full_hash=None):
        url = f"{self.base_url}/files/upload/{upload_id}"
        headers = self.headers.copy()
        if full_hash:
            headers["X-Full-Hash"] = full_hash
        print(f"\n>>> [PATCH] Uploading data to {upload_id}")
        res = requests.patch(url, data=data, headers=headers)
        self._print_res(res)
        return res

    def commit_upload(self, upload_id, full_hash):
        url = f"{self.base_url}/files/upload/{upload_id}/commit"
        headers = self.headers.copy()
        headers["X-Full-Hash"] = full_hash
        print(f"\n>>> [POST] Commit: {upload_id}")
        res = requests.post(url, headers=headers)
        self._print_res(res)
        return res

    def get_messages(self, mode="initial", anchor_id=None, limit=5):
        url = f"{self.base_url}/messages?mode={mode}&limit={limit}"
        if anchor_id:
            url += f"&anchor_id={anchor_id}"
        print(f"\n>>> [GET] Timeline ({mode})")
        res = requests.get(url, headers=self.headers)
        self._print_res(res)
        return res

    def get_thumbnail(self, full_hash):
        url = f"{self.base_url}/files/{full_hash}/thumbnail"
        print(f"\n>>> [GET] Thumbnail: {full_hash}")
        res = requests.get(url, headers=self.headers)
        print(f"<<< [{res.status_code}] Size: {len(res.content)} bytes")
        return res

    def download_file(self, full_hash):
        url = f"{self.base_url}/files/{full_hash}"
        print(f"\n>>> [GET] Download File: {full_hash}")
        res = requests.get(url, headers=self.headers)
        # 获取文件名 (从 Content-Disposition)
        cd = res.headers.get("Content-Disposition", "")
        filename = "unknown"
        if "filename=" in cd:
            filename = cd.split("filename=")[1].strip('"')
        print(f"<<< [{res.status_code}] Filename: {filename}, Size: {len(res.content)} bytes")
        return res, filename
