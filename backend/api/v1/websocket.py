from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from core.websocket_manager import ws_manager
from core.logger import logger
from dependencies import get_auth_service
from db.services.auth_service import AuthService
from core.exceptions import TokenExpired
from schemas.websocket import UdropWSMessage
import json
import time
import asyncio

router = APIRouter(tags=["WebSocket 实时信令"])

@router.get("/ws", 
    summary="[文档专用] WebSocket 信令协议定义", 
    response_model=UdropWSMessage,
    description="""
    ## WebSocket 接入指南
    1. **连接协议**: `ws://` 或 `wss://`
    2. **接入点**: `/api/v1/ws?token={bearer_token}`
    3. **鉴权**: 通过 URL Query 参数传递 Token。
    4. **交互**: 建立连接后，服务端会立即发送 `INIT` 消息。客户端应维持心跳。
    
    ### 核心信令类型:
    - **INIT**: 握手初始化，包含当前 `sync_seq`。
    - **MSG_NEW**: 新消息提醒或附件落盘成功。
    - **MSG_DELETE**: 消息被删除（进入回收站）。
    - **UPLOAD_PROGRESS**: 实时上传进度推送（不增加 sync_seq）。
    - **PONG**: 服务端对客户端 PING 的响应。
    """)
async def websocket_doc_placeholder():
    """该接口仅用于 Swagger 文档展示协议结构，实际逻辑由底层 websocket 处理"""
    return {
        "type": "INIT",
        "sync_seq": 0,
        "data": {"sync_seq": 0, "timestamp": int(time.time())}
    }

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="Bearer Token (用于接入鉴权)")
):
    """
    WebSocket 信令真实入口。
    优化：不再通过 Depends 注入 auth_service，避免在整个长连接期间占用数据库句柄。
    """
    from db.connection import open_connection
    from db.repositories.users import UserRepository
    from db.repositories.devices import DeviceRepository
    from db.repositories.sessions import SessionRepository

    user_uuid = None
    device_id = None
    
    try:
        # 1. 鉴权：使用即用即走的连接
        with open_connection() as conn:
            auth_service = AuthService(UserRepository(conn), DeviceRepository(conn), SessionRepository(conn))
            try:
                session_info = auth_service.is_active_user(token, expire_enable=True)
                user_uuid = session_info["user_uuid"]
                device_id = session_info.get("device_id")
            except TokenExpired:
                logger.warning("WS | 鉴权失败: Token 已过期或非法")
                await websocket.close(code=1008)
                return

        # 2. 建立连接 (Manager 内存管理)
        success = await ws_manager.connect(websocket, user_uuid)
        if not success: return

        # 初次建立连接更新活跃时间
        if device_id:
            with open_connection() as conn:
                AuthService(UserRepository(conn), DeviceRepository(conn), SessionRepository(conn)).touch_device(device_id)

        logger.success(f"WS | 成功握手: 用户 {user_uuid[:8]} (设备: {device_id[:8] if device_id else 'N/A'})")
        
        # 3. 发送握手初始化信息
        await websocket.send_text(json.dumps({
            "type": "INIT",
            "data": {
                "sync_seq": ws_manager.get_current_seq(user_uuid),
                "timestamp": int(time.time())
            }
        }))

        # 4. 维持接收循环
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=65.0)
            except asyncio.TimeoutError:
                logger.warning(f"WS | 链路超时断开: 用户 {user_uuid[:8]}")
                break

            if len(data) > 4096: break

            try:
                message = json.loads(data)
            except json.JSONDecodeError: continue
            
            # 心跳或业务信令交互时，异步非阻塞地更新活跃时间
            if device_id:
                # 这种频率较低的操作，每次交互开启一个新的极短连接是安全的，
                # 相比长连接一直占用，它能让 SQLite 的 WAL 模式更好地进行 Checkpoint。
                with open_connection() as conn:
                    AuthService(UserRepository(conn), DeviceRepository(conn), SessionRepository(conn)).touch_device(device_id)

            if message.get("type") == "PING":
                await websocket.send_text(json.dumps({"type": "PONG", "timestamp": int(time.time())}))
                logger.debug(f"WS | 心跳维持: 用户 {user_uuid[:8]}")

    except WebSocketDisconnect:
        if user_uuid:
            logger.info(f"WS | 客户端主动断开: 用户 {user_uuid[:8]}")
            ws_manager.disconnect(websocket, user_uuid)
    except Exception as e:
        logger.error(f"WS | 链路异常断开: {e}")
        if user_uuid:
            ws_manager.disconnect(websocket, user_uuid)
