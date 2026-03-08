from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    应用配置类
    - 默认值为开发环境配置
    - 生产环境通过 CI/CD 注入环境变量覆盖

    优先级顺序:
    1. 环境变量（系统级）
    2. .env 文件（项目级）
    3. 类中的默认值（代码级）
    """

    # 环境标识
    ENV: Literal["dev", "prod"] = "dev"

    # 应用信息
    VERSION: str = "0.1.1"

    # 服务配置
    HOST: str = "0.0.0.0"
    PORT: int = 5683

    # 数据库配置
    DATABASE_URL: str = "fake"

    # 日志配置
    LOG_PATH: str = "logs/shotmemory.log"
    ROTATION: str = "1 day"
    RETENTION: str = "10 days"

    # CORS 配置（生产环境要变）
    ORIGINS: list[str] = [
        "http://localhost:5173",  # Vite 默认端口
        "http://127.0.0.1:5173",
        # 生产环境域名
        # "https://your-domain.com"
    ]
    METHODS: list[str] = ["*"]
    HEADERS: list[str] = ["*"]

    # Redis 配置
    REDIS_CACHE_URL: str = "redis://127.0.0.1:6379/0"
    REDIS_ARQ_URL: str = "redis://127.0.0.1:6379/1"
    
    # JWT 配置（SECRET_KEY）
    SECRET_KEY: str = "fake"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 存储配置
    UPLOAD_DIR: str = "uploads"
    STATIC_URL_PREFIX: str = "/static"

    # 阿里云 OSS 配置（生产环境通过环境变量注入）
    OSS_ACCESS_KEY_ID: str = ""
    OSS_ACCESS_KEY_SECRET: str = ""
    OSS_BUCKET_NAME: str = ""
    OSS_ENDPOINT: str = ""
    OSS_CDN_DOMAIN: str = ""

    # Cookie 配置
    COOKIE_DOMAIN: str | None = None  # 开发环境设为 None，生产环境设为你的域名
    COOKIE_SECURE: bool = False  # 生产环境设为 True (HTTPS)
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = (
        "lax"  # 跨站请求时cookie是否携带，lax智能模式
    )

    model_config = SettingsConfigDict(
        env_file=".env",  # 从 .env 文件读取
        env_file_encoding="utf-8",
        case_sensitive=True,  # 环境变量区分大小写
        extra="ignore",  # 忽略额外的环境变量
    )


settings = Settings()
