# app/api/v1/__init__.py
from fastapi import APIRouter

# Import the routers defined in your modules (they should each expose `router`)
from .auth import router as auth_router
from .users import router as users_router
from .sessions import router as sessions_router
from .upload import router as upload_router
from .process import router as process_router
from .query import router as query_router

router = APIRouter()
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(users_router,   prefix="/users",   tags=["users"])
router.include_router(sessions_router,prefix="/sessions",tags=["sessions"])
router.include_router(upload_router,  prefix="/upload",  tags=["upload"])
router.include_router(process_router, prefix="/process", tags=["process"])
router.include_router(query_router,   prefix="/query",   tags=["query"])

__all__ = ["router"]
