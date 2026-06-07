import time

from passlib.context import CryptContext

_pwd = CryptContext(schemes=["argon2"], deprecated="auto", argon2__time_cost=2)

ONE_DAY = 86400


def get_time():
    return int(time.time())


class AuthManager:
    @staticmethod
    def get_password_hash(password: str):
        return _pwd.hash(password)

    @staticmethod
    def verify_password_hash(plain_password: str, password_hash: str):
        return _pwd.verify(plain_password, password_hash)
