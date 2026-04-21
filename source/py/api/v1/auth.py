from click import Parameter
from fastapi import APIRouter, Depends, HTTPException
from dependencies import get_auth_service
from schemas.auth import LoginRequest, LoginResponse
from core.exceptions import  ParameterError
from db.services.auth_service import AuthService


router = APIRouter()

@router.post("/login", response_model=LoginResponse,
summary="登陆接口",
description="获取session token，token用于交互其他api")
def login(req: LoginRequest, auth:AuthService = Depends(get_auth_service)) -> LoginResponse:
    if LoginResponse is None:
        raise ParameterError
    return auth.login(
        **req.model_dump()
    )

@router.post("/register", response_model=LoginResponse,
             summary="注册接口",
             description="如果注册成功和登陆一样返回已经登陆的token")
def register(req:LoginRequest, auth:AuthService = Depends(get_auth_service)) -> LoginResponse:
    if LoginResponse is None:
        raise ParameterError
    auth.register_user(req.account, req.password)    
    return login(req, auth)
        

