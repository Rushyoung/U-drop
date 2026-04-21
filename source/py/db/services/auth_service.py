from db.repositories.devices import DeviceRepository
from db.repositories.sessions import SessionRepository
from db.repositories.users import UserRepository
from core.exceptions import AccountRepeat, LoginError
from db.services.utils import AuthManager, ONE_DAY, get_time
from schemas.auth import LoginResponse
import secrets
import uuid

class AuthService:
    def __init__(
        self,
        users: UserRepository,
        devices: DeviceRepository,
        sessions: SessionRepository,
    ) -> None:
        self.users = users
        self.devices = devices
        self.sessions = sessions

    
    def register_user(
        self,
        account: str,
        plain_password: str,
    ) -> bool:
        """ @args:plain_password是明文密码
            @return:false一般是账号重复了,现在会直接返回错误
            @exception:AccountRepear
        """
        if not self.users.check_account(account):
            user_uuid = str(uuid.uuid4())
            password_hash = AuthManager.get_password_hash(plain_password)
            self.users.create_user(
                account=account,
                uuid=user_uuid,
                password_hash=password_hash,
                created_at=get_time()
                )
            return True
        raise AccountRepeat
        # raise NotImplementedError

    def login(
        self,
        account: str,
        password: str,
        device_id: str,
        device_type: int,
        device_name: str | None,
        expire_time: int = 0
    ) -> LoginResponse:
        """
        @brief:  expire time暂时不知道以什么方式传入比较好
        @return: 如果账密错误返回None,否则返回有效token
        @exception:LoginError
        """
        info = self.users.get_by_account(account)
        if info is None:
            # [TODO] 加个统一延时返回
            raise LoginError
        if not AuthManager.verify_password_hash(password, info.password_hash):
            # [TODO] too
            raise LoginError
        row = self.sessions.get_by_user_and_device(info.uuid, device_id)
        if row is None:
            token = secrets.token_urlsafe(32)
            self.sessions.create_session(
                token, 
                info.uuid, 
                device_id, 
                get_time()+ONE_DAY * info.expire_set
                )
            self.devices.create_device(
                device_id,
                info.uuid,
                device_type,
                device_name if device_name else "未知设备名称",
                get_time()
            )
        else:
            token = row["bearer_token"]
        return LoginResponse(code="200", bearer=token, msg=f"{info.account}登陆成功")
        

        # raise NotImplementedError
    
    def is_active_user(
            self,
            bearer: str,
            now:    int,
            expire_enable:  bool
    )->bool:
        """@return:False是无效或者过期token
        """
        info = self.sessions.get_by_token(bearer)
        if info is None:
            raise 
            
        if expire_enable:
            if info["expire_time"] < now:
                return False
        
        return True
    


    def logout(self, bearer_token: str) -> None:
        count = self.sessions.delete_by_token(bearer_token)
        if count == 0:
            raise IndexError # [TODO] 完善错误模型
        # raise NotImplementedError