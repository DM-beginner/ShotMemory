import contextlib
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from core.config import settings
from core.custom_exception import BusinessError
from core.database import close_db, warm_up
from core.exception_handler import (
    business_error_handler,
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from core.logger import setup_logging
from core.root_router import router as root_router
from middlewares.logger_middleware import log_requests_middleware
from services.auth.routers.auth_router import router as auth_router
from services.photo_story.routers.photo_router import router as photo_router
from services.photo_story.routers.story_router import router as story_router
from services.photo_story.routers.upload_router import router as upload_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 应用启动时的逻辑（如果需要的话）
    setup_logging()
    await warm_up()
    yield
    # 应用关闭时的逻辑（如果需要的话）
    await close_db()


def register_middleware(_app: FastAPI) -> None:
    # 类中间件注册
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ORIGINS,
        allow_credentials=True,
        allow_methods=settings.METHODS,
        allow_headers=settings.HEADERS,
    )
    _app.middleware("http")(log_requests_middleware)  # 函数中间件注册


def register_exception_handlers(_app: FastAPI) -> None:
    """
    注册全局异常处理器
    注意顺序：从具体到一般（BusinessError -> HTTPException -> ValidationError -> Exception）
    """
    _app.add_exception_handler(BusinessError, business_error_handler)  # type: ignore[arg-type]
    _app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    _app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    _app.add_exception_handler(Exception, general_exception_handler)


def register_static_files(_app: FastAPI) -> None:
    """
    挂载静态文件服务
    - 开发环境下，通过 /static 路径访问本地上传的文件
    - 例如: http://localhost:5683/static/uploads/xxx.jpg
    """
    if settings.ENV == "dev":
        from pathlib import Path

        # 确保 uploads 目录存在
        Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
        _app.mount(
            settings.STATIC_URL_PREFIX,
            StaticFiles(directory="."),
            name="static",
        )


def register_routes(_app: FastAPI) -> None:
    prefix_version = "/v1"
    _app.include_router(router=root_router)
    _app.include_router(router=auth_router, prefix=f"{prefix_version}")
    _app.include_router(router=upload_router, prefix=f"{prefix_version}")
    _app.include_router(router=photo_router, prefix=f"{prefix_version}")
    _app.include_router(router=story_router, prefix=f"{prefix_version}")


def create_app() -> FastAPI:
    _app = FastAPI(
        title="Example APP",
        version=settings.VERSION,
        lifespan=lifespan,
        docs_url="/docs",
    )
    register_middleware(_app)
    register_exception_handlers(_app)
    register_routes(_app)
    register_static_files(_app)

    return _app


def run() -> None:
    with contextlib.suppress(ImportError):
        import uvloop  # pyright: ignore[reportMissingImports]

        uvloop.install()

    if settings.ENV == "dev":
        uvicorn.run(
            "main:app",
            host=settings.HOST,
            port=settings.PORT,
            log_level="info",
            ws_ping_interval=10,
            loop="auto",
            reload=True,
        )
    else:
        uvicorn.run(
            create_app(),
            host=settings.HOST,
            port=settings.PORT,
            log_level="error",
            ws_ping_interval=10,
            loop="auto",
        )


app = create_app()

if __name__ == "__main__":
    # gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:9000 app_loader:app
    run()
