


class UdropException(Exception):
    def __init__(self, code : int, message : str) -> None:
        self.code = code
        self.message = message

class ParameterError(UdropException):
    def __init__(self,message: str = "参数不匹配") -> None:
        super().__init__(400, message)

class LoginError(UdropException):
    def __init__(self) -> None:
        super().__init__(code=401, message="登陆失败，账号或密码错误")


class AccountRepeat(UdropException):
    def __init__(self) -> None:
        code = 409
        super().__init__(code, "该账号已经存在")
        

class TokenExpired(UdropException):
    def __init__(self) -> None:
        code = 401
        message = "已过期的登录!"
        super().__init__(code, message)