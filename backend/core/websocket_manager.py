from fastapi import WebSocket
from typing import Dict, List
import json
from core.logger import logger

class ConnectionManager:
    def __init__(self):
        # 活跃连接池: { user_uuid: [WebSocket, ...] }
        self.active_connections: Dict[str, List[WebSocket]] = {}
        
        # Seq 内存缓存: { user_uuid: current_seq }
        self._seq_cache: Dict[str, int] = {}

    async def connect(self, websocket: WebSocket, user_uuid: str):
        """建立连接并注册"""
        # 安全加固：限制单用户最大连接数，防止资源耗尽攻击
        MAX_CONNECTIONS_PER_USER = 10
        current_conns = self.active_connections.get(user_uuid, [])
        if len(current_conns) >= MAX_CONNECTIONS_PER_USER:
            logger.warning(f"WS | 拒绝连接: 用户 {user_uuid[:8]} 已达到最大并发连接数 ({MAX_CONNECTIONS_PER_USER})")
            await websocket.close(code=1008) # Policy Violation
            return False

        await websocket.accept()
        if user_uuid not in self.active_connections:
            self.active_connections[user_uuid] = []
        self.active_connections[user_uuid].append(websocket)
        logger.info(f"WS | 用户 {user_uuid[:8]} 已上线 | 当前端数: {len(self.active_connections[user_uuid])}")
        return True

    def disconnect(self, websocket: WebSocket, user_uuid: str):
        """断开连接并清理"""
        if user_uuid in self.active_connections:
            if websocket in self.active_connections[user_uuid]:
                self.active_connections[user_uuid].remove(websocket)
            if not self.active_connections[user_uuid]:
                del self.active_connections[user_uuid]
        logger.info(f"WS | 用户 {user_uuid[:8]} 已下线")

    async def broadcast_to_user(self, user_uuid: str, payload: dict, bump_seq: bool = True):
        """
        向特定用户的所有在线设备广播信令。
        """
        # 1. 维护 Seq
        if bump_seq:
            current_seq = self._seq_cache.get(user_uuid, 0) + 1
            self._seq_cache[user_uuid] = current_seq
            payload["sync_seq"] = current_seq
        else:
            payload["sync_seq"] = self._seq_cache.get(user_uuid, 0)

        # 2. 查找连接
        connections = self.active_connections.get(user_uuid, [])
        if not connections:
            return

        # 3. 执行发送
        dead_connections = []
        message_str = json.dumps(payload)
        
        logger.debug(f"WS | 发送信号给用户 {user_uuid[:8]}: {payload.get('type')} | Seq: {payload.get('sync_seq')}")
        
        for ws in connections:
            try:
                await ws.send_text(message_str)
            except Exception as e:
                logger.warning(f"WS | 信号投递失败 (连接已死): {e}")
                dead_connections.append(ws)

        # 4. 清理
        for dead in dead_connections:
            self.disconnect(dead, user_uuid)

    def get_current_seq(self, user_uuid: str) -> int:
        return self._seq_cache.get(user_uuid, 0)

# 全局单例
ws_manager = ConnectionManager()
