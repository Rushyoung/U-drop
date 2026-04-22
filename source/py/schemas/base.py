from typing import TypeVar, Generic, Optional, Any
from pydantic import BaseModel

T = TypeVar("T")

class ResponseSchema(BaseModel, Generic[T]):
    """统一响应模型"""
    code: int = 200
    message: str = "success"
    data: Optional[T] = None

    @classmethod
    def success(cls, data: Any = None, message: str = "success"):
        return cls(code=200, message=message, data=data)

    @classmethod
    def error(cls, message: str = "error", code: int = 500):
        return cls(code=code, message=message, data=None)
