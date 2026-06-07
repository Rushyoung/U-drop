from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field


class WSInitData(BaseModel):
    sync_seq: int = Field(..., description="当前最新的同步序列号")
    timestamp: int = Field(..., description="服务端当前时间戳")


class WSMsgNewData(BaseModel):
    message_id: int = Field(..., description="新消息的 ID")
    file_hash: Optional[str] = Field(None, description="若是附件落位，则包含文件哈希")


class WSMsgDeleteData(BaseModel):
    message_id: int = Field(..., description="被删除的消息 ID")


class WSUploadProgressData(BaseModel):
    upload_id: str = Field(..., description="上传任务 UUID")
    received_size: int = Field(..., description="已接收字节数")
    total_size: int = Field(..., description="总文件大小")


class WSDeviceUpdateData(BaseModel):
    device_id: str = Field(..., description="变更名称的设备 ID")
    device_name: str = Field(..., description="设备的新名称")


class UdropWSMessage(BaseModel):
    """WebSocket 统一信令格式"""

    type: str = Field(
        ...,
        description="信令类型: INIT, MSG_NEW, MSG_DELETE, UPLOAD_PROGRESS, DEVICE_UPDATE, PONG",
    )
    sync_seq: Optional[int] = Field(None, description="自增同步序列号")
    data: Optional[
        Union[
            WSInitData,
            WSMsgNewData,
            WSMsgDeleteData,
            WSUploadProgressData,
            WSDeviceUpdateData,
            Dict[str, Any],
        ]
    ] = Field(None, description="信令负载数据")


class WSPingMessage(BaseModel):
    """客户端心跳请求"""

    type: str = Field("PING", pattern="^PING$")
