from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyCookie

from core.config import settings
from core.database import SessionDep
from services.auth.models.user_model import User
from services.auth.repos import UserRepo
from services.auth.schemas.token_schema import TokenPayload

# Cookie 名称常量 (与 auth_router 保持一致)
ACCESS_TOKEN_COOKIE = "access_token"

# 使用 APIKeyCookie 让 Swagger UI 支持 Cookie 认证
cookie_scheme = APIKeyCookie(name=ACCESS_TOKEN_COOKIE, auto_error=False)


async def get_token_from_cookie(
    token: str | None = Depends(cookie_scheme),
) -> str:
    """
    从 Cookie 中提取 access_token
    支持 Swagger UI 测试
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


TokenDep = Annotated[str, Depends(get_token_from_cookie)]


async def get_current_user(
    token: TokenDep,
    db: SessionDep,
) -> User:
    """
    解析 Cookie 中的 access_token，获取当前登录用户
    """
    try:
        # 解码 Token
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",  # 前端根据这个 detail 判断是否要刷新
        ) from None
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from None

    # 验证 Token 类型 (防止用 Refresh Token 访问接口)
    if token_data.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    # 查库获取用户
    user = await UserRepo.get_user_by_id(db, UUID(token_data.sub))

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_deleted:
        raise HTTPException(status_code=400, detail="Inactive user")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
