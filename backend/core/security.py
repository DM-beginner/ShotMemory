from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from core.config import settings  # 假设你的配置在这里

# 1. 密码哈希配置 (使用 bcrypt)
# 配置说明：
# 1. 内存：64MB (标准安全水位)
# 2. 时间：4轮 (因为并行度降了，稍微加一点时间成本补足安全性)
# 3. 并行：1线程 (专门针对 Python Web 环境优化，避免 CPU 争抢)


pwd_context = PasswordHash.recommended()


# --- 密码相关工具 ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    核心逻辑: 密码哈希是不可逆的（你不能把乱码变回 "123456"）。

    1. 提取 hashed_password 里的“盐”（Bcrypt 把盐存在了哈希字符串里）。
    2. 用这个“盐”对用户刚刚输入的 plain_password 再进行一次哈希。
    3. 比较新计算出的哈希值和数据库里的哈希值是否完全一致。
    """

    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    功能: 把用户输入的明文密码（如 "123456"）转换成一串乱码（哈希值）。

    重要概念 - 加盐 (Salting):
    Bcrypt 最神奇的地方在于：你每次对 "123456" 进行哈希，得到的结果都是不一样的！
    这是因为 Bcrypt 会自动生成一段随机字符串（称为“盐/Salt”），混入密码中一起加密。
    结果样子: $2b$12$K1... (以 $2b$ 开头，包含算法版本、难度、盐和哈希值)。
    """
    return pwd_context.hash(password)


# --- Token 相关工具 ---
def create_token(
    subject: str | Any, expires_delta: timedelta, token_type: str = "access"
) -> str:
    """
    生成 JWT Token (Access 或 Refresh)
    """
    now = datetime.now(UTC)
    expire = now + expires_delta

    to_encode = {
        "exp": expire,  # Expiration Time (过期时间)
        "iat": now,  # Issued At (签发时间)
        "sub": str(subject),  # sub 存 user_id
        "type": token_type,  # 重要：区分 token 类型
    }

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_access_token(user_id: UUID) -> str:
    return create_token(
        user_id, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), "access"
    )


def create_refresh_token(user_id: UUID) -> str:
    return create_token(
        user_id, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), "refresh"
    )
