from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseSchema(BaseModel, Generic[T]):
    """统一响应模型"""

    success: bool = Field(True, description="是否成功")
    code: int = Field(
        200, description="状态码: 200成功, 401未授权, 403拒绝, 404未找到, 500错误"
    )
    message: str = Field("success", description="操作结果提示文本")
    data: Optional[T] = Field(None, description="业务数据载荷")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "code": 200,
                "message": "Operation successful",
                "data": None,
            }
        }
    }

    @classmethod
    def ok(cls, data: Any = None, message: str = "success"):
        return cls(success=True, code=200, message=message, data=data)

    @classmethod
    def fail(cls, message: str = "error", code: int = 500):
        return cls(success=False, code=code, message=message, data=None)


class ErrorResponse(BaseModel):
    """通用错误响应结构 (用于文档展示)"""

    success: bool = Field(False, description="是否成功")
    code: int = Field(..., description="业务错误码")
    message: str = Field(..., description="错误原因描述")
    data: None = None


COMMON_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Token 缺失或已过期"},
    403: {"model": ErrorResponse, "description": "权限不足 (例如非管理员访问管理接口)"},
    404: {
        "model": ErrorResponse,
        "description": "资源不存在 (例如消息、文件或上传任务已失效)",
    },
}
