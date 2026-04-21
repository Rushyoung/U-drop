from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    account:str
    uuid:str

class UserPublic(UserBase):
    created_at:int

class UserInternal(UserPublic):
    password_hash:str
    expire_set:int


class LoginRequest(BaseModel):
    account: str
    password: str
    device_id: str
    device_type: int
    device_name: Optional[str]
    expire_time: int

class LoginResponse(BaseModel):
    code:str
    bearer:Optional[str]
    msg:str

    
