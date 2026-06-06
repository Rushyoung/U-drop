# U-Drop API 接口定义 (v0.5.1)

## Phase 1: 账号与设备
- `POST /auth/register`: 用户注册
- `POST /auth/login`: 登录（支持 `single_use`, `expire_in`）
- `GET  /auth/me`: 获取个人信息（含配额、已用量、Seq）
- `PUT  /auth/settings`: 更新设置（如 `trash_expire_days`）
- `PUT  /auth/device`: 更新当前设备名称
- `PUT  /auth/password`: 修改登录密码
- `GET  /auth/devices`: 获取已登录设备列表
- `DELETE /auth/devices/{id}`: 强制注销特定设备

## Phase 2: 消息与实时信令
- `POST /messages`: 创建消息（返回 `upload_id` 清单）
- `GET  /messages`: 拉取时间线（滑动窗口分页）
- `DELETE /messages/{id}`: 软删除（进回收站）
- `GET  /messages/trash`: 查看回收站
- `POST /messages/{id}/restore`: 恢复消息
- `DELETE /messages/trash/empty`: 清空回收站（释放配额）
- **`WS /ws`**: WebSocket 实时信令通道

## Phase 3: 极速文件流与配额管理
- `PATCH /files/upload/{upload_id}`: 流式上传（支持 Proof of Possession 秒传）
- `POST  /files/upload/{upload_id}/commit`: 提交哈希校验并入库
- `GET   /files/large`: 大文件猎手（返回引用详情，助力精准释放）
- `DELETE /files/messages/{mid}/attachments/{aid}`: 剥离附件（精细化释放空间）
- `GET   /files/attachments/{id}/download`: 下载附件 (逻辑寻址)
- `GET   /files/attachments/{id}/thumbnail`: 获取缩略图 (逻辑寻址)

## Phase 4: 分享中心
- `POST /share/file`: 创建文件分享（入参为逻辑 `attachment_id`）
- `GET  /share/{id}`: 匿名提取文件

## Phase 5: 系统管理与维护 (Manage)
- `GET  /system/status`: 探测系统初始化状态及配置
- `POST /system/setup`: 首次运行初始化 (创建 Admin)
- `GET  /manage/settings`: 管理员查看全局配置
- `PUT  /manage/settings`: 管理员热更新系统设置
- `GET  /manage/users`: 查看全量用户列表
- `PUT  /manage/users/{uuid}/quota`: 调整用户配额
- `PUT  /manage/users/{uuid}/status`: 启用/禁用用户
- `POST /manage/factory_reset`: 工厂重置 (抹除业务数据)
