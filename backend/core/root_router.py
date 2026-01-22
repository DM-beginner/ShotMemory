from fastapi import APIRouter
from starlette.responses import RedirectResponse

router = APIRouter()


@router.get("/", include_in_schema=False)
async def root():
    # 访问首页时，自动跳转到 /docs
    return RedirectResponse(url="/docs")
