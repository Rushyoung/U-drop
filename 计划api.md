## 时间线功能 API（v2）

本版与旧接口不兼容：时间线拉取从 offset/limit 改为按“当前消息的 id”分段拉取。

## 通用约定

- 鉴权：`Authorization: Bearer <token>`
- 时间线稳定排序：`timestamp DESC, id DESC`
- `anchor_id`：当前消息的 `id`（用于继续向前或向后拉取）
- `limit` 建议范围：`1..100`，默认 `50`
- 软删除：服务端设置 `is_deleted=1`，客户端通过同步接口收敛删除

### 1. 拉取时间线窗口
`GET /api/v1/messages?mode=initial|before|after&anchor_id=&limit=50&keyword=&hashtag=`

参数说明
- `mode=initial`：首次拉取最近一屏
- `mode=before`：向更旧方向回填，要求 `anchor_id`
- `mode=after`：向更新方向增量拉取，要求 `anchor_id`
- `keyword`/`hashtag`：可选过滤条件

响应示例
```json
{
  "items": [
    {
      "id": 1024,
      "mime_type": "text/plain",
      "device_name": "Pixel 8",
      "device_type": "android",
      "send_time": 1710000000,
      "content": "hello",
      "hashtags": ["work"],
      "file_info": {
        "file_id": "blake3_xxx",
        "file_name": "doc.pdf",
        "file_size": 1203,
        "thumbnail_url": "..."
      }
    }
  ],
  "page": {
    "oldest_id": 900,
    "newest_id": 1024,
    "has_more_before": true,
    "has_more_after": false,
    "next_before_anchor": 900,
    "next_after_anchor": 1024
  },
  "sync": {
    "next_seq": 2234,
    "server_time": 1710000123
  }
}
```

状态码
- `200 OK`：拉取成功
- `400 Bad Request`：参数非法（如缺少 `anchor_id`）
- `401 Unauthorized`：未登录或 token 失效

### 2. 增量同步（含删除收敛）
`GET /api/v1/messages/sync?after_seq=0&limit=200`

用途
- 客户端收到 `REFRESH_TIMELINE` 信号后调用
- 设备离线重连后补齐变更
- 返回新增/更新与删除事件，确保“删除消息”跨设备一致

响应示例
```json
{
  "upserts": [
    {
      "id": 1025,
      "mime_type": "text/plain",
      "send_time": 1710000130,
      "content": "new msg"
    }
  ],
  "deleted_ids": [1001, 1002],
  "next_seq": 2240,
  "has_more": false
}
```

客户端合并规则
- 先应用 `upserts`
- 再应用 `deleted_ids`
- 以 `id` 去重，重复处理同一批数据时结果应保持一致
- 持久化 `next_seq` 作为下次 `after_seq`

### 3. 创建消息
`POST /api/v1/messages`

Headers
- `Authorization: Bearer <token>`
- `Content-Type: application/json`

请求体
```json
{
  "content": "text | fasthash",
  "hash_tag": ""
}
```

响应示例
```json
{
  "status": "created",
  "message_id": 1026,
  "sync_seq": 2241,
  "addition": "upload id"
}
```

状态码
- `201 Created`：已创建
- `202 Accepted`：更多操作（需要后续处理）

### 4. 更新上传状态
`PATCH /api/v1/uploads/{upload_id}`

### 5. 提交上传完成
`POST /api/v1/uploads/{upload_id}/commit`

### 6. 获取文件
`GET /api/v1/files/{full_hash.ext}`

Headers
- `Authorization: Bearer <token>`

### 7. 删除消息
`DELETE /api/v1/messages/{msgid}`

语义
- 软删除：设置 `is_deleted=1`
- 产生同步事件：提升 `sync_seq`
- 服务端向在线设备下发 `REFRESH_TIMELINE`

响应示例
```json
{
  "status": "deleted",
  "message_id": 1024,
  "sync_seq": 2242
}
```

### 8. 获取在线设备
`GET /api/v1/devices`

### 9. WebSocket 信令（控制面）
`GET /api/v1/ws`

事件示例
```json
{
  "type": "REFRESH_TIMELINE",
  "latest_message_id": 1026,
  "latest_seq": 2242
}
```

说明
- WebSocket 不下发消息正文
- 客户端收到后调用 `GET /api/v1/messages/sync?after_seq=...`
