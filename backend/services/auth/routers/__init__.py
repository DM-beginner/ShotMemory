from services.auth.routers.auth_router import router as auth_router
from services.auth.routers.user_deps import CurrentUser

__all__ = ["CurrentUser", "auth_router"]
