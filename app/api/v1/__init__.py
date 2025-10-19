# app/api/v1/__init__.py
from fastapi import APIRouter

# Import the routers defined in your modules
from .auth import router as auth_router
from .users import router as users_router
from .sessions import router as sessions_router
from .upload import router as upload_router
from .process import router as process_router
from .query import router as query_router
from .stats import router as stats_router

router = APIRouter()

# Grouped includes
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(users_router, prefix="/users", tags=["users"])
router.include_router(sessions_router, tags=["sessions"])
router.include_router(upload_router, tags=["upload"])
router.include_router(process_router, tags=["process"])
router.include_router(query_router, tags=["query"])
router.include_router(stats_router, prefix="/stats", tags=["stats"])

__all__ = ["router"]
