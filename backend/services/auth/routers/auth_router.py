from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from fastapi import APIRouter, Cookie
from fastapi.responses import ORJSONResponse

from core import security
from core.base_code import APIStatus
from core.base_schema import BaseResponse
from core.config import settings
from core.custom_exception import BusinessError
from core.database import SessionDep
from core.unify_response import UnifyResponse
from services.auth.models.refresh_token_model import RefreshToken
from services.auth.models.user_model import User
from services.auth.repos import RefreshTokenRepo, UserRepo
from services.auth.schemas.token_schema import (
    AuthResponseData,
    LoginRequest,
    RegisterRequest,
    TokenPayload,
)
from services.auth.schemas.user_schema import RegisterResponseData

router = APIRouter(tags=["auth"], prefix="/auth")

# Cookie 名称常量
ACCESS_TOKEN_COOKIE = "access_token"
REFRESH_TOKEN_COOKIE = "refresh_token"


def _set_auth_cookies(
    response: ORJSONResponse, access_token: str, refresh_token: str
) -> None:
    """
    设置认证相关的 HTTPOnly Cookie
    - access_token: 短期有效，用于 API 认证
    - refresh_token: 长期有效，用于刷新 access_token
    """
    # Access Token Cookie (短期)
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,  # 🔐 JavaScript 无法访问
        secure=settings.COOKIE_SECURE,  # 生产环境开启 HTTPS
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/",
    )

    # Refresh Token Cookie (长期)
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/v1/auth",  # 🔐 仅在 auth 路径下发送，减少泄露风险
    )


def _clear_auth_cookies(response: ORJSONResponse) -> None:
    """清除认证相关的 Cookie"""
    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE,
        path="/",
        domain=settings.COOKIE_DOMAIN,
    )
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE,
        path="/v1/auth",
        domain=settings.COOKIE_DOMAIN,
    )


def _user_valid_verify(user: User) -> None:
    """校验用户状态是否正常（未被删除、未被冻结）"""
    if user.is_deleted:
        raise BusinessError(
            code=APIStatus.USER_DELETED.code,
            message=APIStatus.USER_DELETED.msg,
            status_code=400,
        )


def _user_exist_verify(user: User | None) -> None:
    """如果用户不存在，报错"""
    if not user:
        raise BusinessError(
            code=APIStatus.USER_NOT_FOUND.code,
            message=APIStatus.USER_NOT_FOUND.msg,
            status_code=404,
        )


def _user_not_exist_verify(user: User | None, field: str = "账号") -> None:
    """如果用户存在，报错（用于注册时检查）"""
    if user:
        raise BusinessError(
            code=APIStatus.USER_EXISTS.code, message=f"{field}已被注册", status_code=400
        )


def _user_password_verify(user: User, password: str) -> None:
    """校验密码是否正确"""
    if not security.verify_password(password, user.hashed_password):
        raise BusinessError(
            code=APIStatus.USER_PASSWORD_ERROR.code,
            message=APIStatus.USER_PASSWORD_ERROR.msg,
            status_code=401,
        )


def _refresh_token_exist_verify(refresh_token: str | None) -> None:
    """校验 refresh_token 是否提供"""
    if not refresh_token:
        raise BusinessError(
            code=APIStatus.TOKEN_NOT_PROVIDED.code,
            message=APIStatus.TOKEN_NOT_PROVIDED.msg,
            status_code=401,
        )


def _refresh_token_type_verify(payload: TokenPayload) -> None:
    """校验 token 类型是否为 refresh"""
    if payload.get("type") != "refresh":
        raise BusinessError(
            code=APIStatus.TOKEN_TYPE_ERROR.code,
            message=APIStatus.TOKEN_TYPE_ERROR.msg,
            status_code=401,
        )


def _db_token_exist_verify(db_token: RefreshToken | None) -> None:
    """校验数据库中的 token 是否存在"""
    if not db_token:
        raise BusinessError(
            code=APIStatus.TOKEN_INVALID.code,
            message=APIStatus.TOKEN_INVALID.msg,
            status_code=401,
        )


async def _db_token_expired_verify(db: SessionDep, db_token: RefreshToken) -> None:
    """校验 token 是否过期，如果过期则删除"""
    if db_token.expires_at <= datetime.now(UTC):
        await RefreshTokenRepo.delete_refresh_token(db, db_token)
        raise BusinessError(
            code=APIStatus.TOKEN_EXPIRED.code,
            message=APIStatus.TOKEN_EXPIRED.msg,
            status_code=401,
        )


@router.post("/register", response_model=BaseResponse[RegisterResponseData])
async def register(
    form_data: RegisterRequest,
    db: SessionDep,
):
    """
    用户注册：创建新用户账号
    - 支持邮箱注册或手机号注册
    - 邮箱和手机号至少提供一个
    """
    # 1. 检查邮箱是否已存在
    if form_data.email:
        existing_user = await UserRepo.get_user_by_email(db, form_data.email)
        _user_not_exist_verify(existing_user, "邮箱")

    # 2. 检查手机号是否已存在
    if form_data.phone:
        existing_user = await UserRepo.get_user_by_phone(db, form_data.phone)
        _user_not_exist_verify(existing_user, "手机号")

    # 3. 创建用户
    user = await UserRepo.create_user(
        db=db,
        name=form_data.name,
        email=form_data.email,
        phone=form_data.phone,
        password=form_data.password,
    )

    # 4. 返回用户信息
    response_data = RegisterResponseData(
        id=str(user.id),
        name=user.name,
        email=user.email,
        phone=user.phone,
        created_at=user.created_at.isoformat(),
    )
    return UnifyResponse.success(data=response_data.model_dump(), message="注册成功")


@router.post("/login", response_model=BaseResponse[AuthResponseData])
async def login(
    form_data: LoginRequest,
    db: SessionDep,
):
    """
    用户登录：校验邮箱/手机号和密码，通过 HTTPOnly Cookie 返回双 Token
    - 支持邮箱登录或手机号登录
    - 前端需要生成并持久化存储 device_id（UUID）
    - 同一设备重复登录会更新该设备的 token
    - 不同设备登录会创建新的 token（支持多设备）
    """
    # 1. 查找用户（根据邮箱或手机号）
    user = await UserRepo.get_user_by_email_or_phone(
        db, email=form_data.email, phone=form_data.phone
    )

    # 2. 安全校验
    _user_exist_verify(user)
    _user_password_verify(user, form_data.password)
    _user_valid_verify(user)

    # 3. 生成双 Token
    access_token = security.create_access_token(user.id)
    refresh_token = security.create_refresh_token(user.id)

    # 4. 存入数据库（使用 device_id 作为 UPSERT 锚点）
    expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    # upsert_refresh_token 内部已使用 CTE 同时更新 last_active_at
    await RefreshTokenRepo.upsert_refresh_token(
        db=db,
        user_id=user.id,
        device_id=form_data.device_id,
        refresh_token=refresh_token,
        expires_at=expires_at,
    )

    # 5. 创建响应并设置 Cookie
    response_data = AuthResponseData(message="登录成功", token_type="bearer")
    response = UnifyResponse.success(
        data=response_data.model_dump(),
        message="登录成功",
    )
    _set_auth_cookies(response, access_token, refresh_token)

    return response


@router.post("/refresh", response_model=BaseResponse[AuthResponseData])
async def refresh_token(
    db: SessionDep,
    refresh_token: str | None = Cookie(None, alias=REFRESH_TOKEN_COOKIE),
):
    """
    使用 Refresh Token 换取新的 Access Token
    - Refresh Token 从 HTTPOnly Cookie 中自动读取
    - 实现 Token 轮转：每次刷新都生成新的 refresh_token
    - 验证数据库中的 token 状态（是否撤销、是否已使用）
    """
    _refresh_token_exist_verify(refresh_token)

    try:
        # 1. 解码并校验 Refresh Token
        payload: TokenPayload = jwt.decode(
            refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        _refresh_token_type_verify(payload)

        user_id = UUID(payload["sub"])

        # 2. 验证数据库中的 token
        db_token = await RefreshTokenRepo.get_refresh_token(db, refresh_token)

        _db_token_exist_verify(db_token)
        await _db_token_expired_verify(db, db_token)

        # 4. 查用户是否存在
        user = await UserRepo.get_user_by_id(db, user_id)

        _user_exist_verify(user)
        _user_valid_verify(user)

        # 5. 生成新的 token（使用原 device_id 作为 UPSERT 锚点）
        new_access_token = security.create_access_token(user_id)
        new_refresh_token = security.create_refresh_token(user_id)

        new_expires_at = datetime.now(UTC) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        # upsert_refresh_token 内部已使用 CTE 同时更新 last_active_at
        await RefreshTokenRepo.upsert_refresh_token(
            db=db,
            user_id=user_id,
            device_id=db_token.device_id,  # 使用原 token 的 device_id
            refresh_token=new_refresh_token,
            expires_at=new_expires_at,
        )

        response = UnifyResponse.success(
            data={"message": "Token 刷新成功", "token_type": "bearer"},
            message="Token 刷新成功",
        )
        _set_auth_cookies(response, new_access_token, new_refresh_token)

        return response

    except jwt.ExpiredSignatureError:
        raise BusinessError(
            code=APIStatus.TOKEN_EXPIRED.code,
            message=APIStatus.TOKEN_EXPIRED.msg,
            status_code=401,
        ) from None
    except jwt.PyJWTError:
        raise BusinessError(
            code=APIStatus.TOKEN_INVALID.code,
            message=APIStatus.TOKEN_INVALID.msg,
            status_code=401,
        ) from None


@router.post("/logout", response_model=BaseResponse[AuthResponseData])
async def logout(
    db: SessionDep,
    refresh_token: str | None = Cookie(None, alias=REFRESH_TOKEN_COOKIE),
):
    """
    用户登出：删除 refresh_token 并清除认证 Cookie
    """
    # 如果有 refresh_token，则删除它
    if refresh_token:
        try:
            db_token = await RefreshTokenRepo.get_refresh_token(db, refresh_token)
            if db_token:
                await RefreshTokenRepo.delete_refresh_token(db, db_token)
        except Exception:
            # 即使删除失败也继续清除 Cookie
            pass

    response_data = AuthResponseData(message="退出登录成功", token_type="bearer")
    response = UnifyResponse.success(
        data=response_data.model_dump(),
        message="退出登录成功",
    )
    _clear_auth_cookies(response)
    return response


@router.delete("/account", response_model=BaseResponse[AuthResponseData])
async def delete_account(
    db: SessionDep,
    refresh_token: str | None = Cookie(None, alias=REFRESH_TOKEN_COOKIE),
):
    """
    注销账号：软删除用户并删除 refresh_token
    """

    _refresh_token_exist_verify(refresh_token)

    try:
        # 1. 解码 token 获取 user_id
        payload = jwt.decode(
            refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id = UUID(payload["sub"])

        # 2. 查询用户
        user = await UserRepo.get_user_by_id(db, user_id)
        _user_exist_verify(user)
        _user_valid_verify(user)

        # 3. 软删除用户
        await UserRepo.soft_delete_user(db, user)

        # 4. 删除 refresh_token
        await RefreshTokenRepo.delete_refresh_token_by_user_id(db, user_id)

        # 5. 清除 Cookie
        response_data = AuthResponseData(message="账号已注销", token_type="bearer")
        response = UnifyResponse.success(
            data=response_data.model_dump(),
            message="账号已注销",
        )
        _clear_auth_cookies(response)
        return response

    except jwt.PyJWTError:
        raise BusinessError(
            code=APIStatus.TOKEN_INVALID.code,
            message=APIStatus.TOKEN_INVALID.msg,
            status_code=401,
        ) from None
