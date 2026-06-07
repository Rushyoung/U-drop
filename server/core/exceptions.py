class UdropException(Exception):
    def __init__(self, code : int, message : str) -> None:
        self.code = code
        self.message = message

class ParameterError(UdropException):
    def __init__(self, message: str = "参数不匹配") -> None:
        super().__init__(400, message)

class LoginError(UdropException):
    def __init__(self) -> None:
        super().__init__(code=401, message="登陆失败，账号或密码错误")

class AccountRepeat(UdropException):
    def __init__(self) -> None:
        super().__init__(409, "该账号已经存在")

class TokenExpired(UdropException):
    def __init__(self) -> None:
        super().__init__(401, "已过期的登录!")

class TaskNotFound(UdropException):
    def __init__(self, message: str = "上传任务不存在或已失效") -> None:
        super().__init__(404, message)

class ForbiddenError(UdropException):
    def __init__(self, message: str = "无权进行此操作") -> None:
        super().__init__(403, message)

class HashMismatch(UdropException):
    def __init__(self, message: str = "文件哈希校验不一致") -> None:
        super().__init__(400, message)

class InternalError(UdropException):
    def __init__(self, message: str = "服务器内部错误") -> None:
        super().__init__(500, message)
