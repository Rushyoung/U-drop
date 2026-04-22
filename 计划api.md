# U-Drop 接口文档 (同步当前实现)

## 通用返回格式
所有接口都返回这个格式：
```json
{
  "code": 200,      // 200是成功，其他是错
  "message": "...", // 提示信息
  "data": { ... }   // 真正的数据
}
```

## 1. 消息模块 (/api/v1/messages)

### 创建消息 [POST]
请求：
```json
{
  "content": "文字内容",
  "file_name": "文件名.ext", // 没文件就不传
  "total_size": 12345,
  "sparse_hash": "指纹",
  "tags": ["标签1"]
}
```
返回 (带文件时)：
```json
{
  "code": 200,
  "data": {
    "status": "accepted",
    "message_id": 1,
    "upload_id": "uuid-xxx" // 拿这个去传文件
  }
}
```

## 2. 文件上传模块 (/api/v1/files)

### 流式上传 [PATCH] `/upload/{upload_id}`
- **Header**: `X-Full-Hash` (可选，本地算完就带上)
- **Body**: 原始二进制流
- **逻辑**: 
    - 传的时候服务端会盯着 `X-Full-Hash`。
    - 发现重复了直接回 `200` 并报 `deduplicated`，这时候客户端就该停了。

### 提交上传 [POST] `/upload/{upload_id}/commit`
- **Header**: `X-Full-Hash` (必填)
- **逻辑**: 
    - 服务端核对哈希，对不上直接报 `400`。
    - 对上了就转存文件，把消息表里的 `file_hash` 补全。

## 3. 时间线模块 (待完善)
- **获取消息**: `GET /api/v1/messages`
- **逻辑**: 以后会用 `anchor_id` 来拉，保证翻页不重不漏。
- **状态提示**: 如果消息的 `file_hash` 是空的，前端记得标个“上传中”。
