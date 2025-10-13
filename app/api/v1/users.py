from fastapi import APIRouter, HTTPException, Depends, status
from app.domain.models import UserIn, UserOut
from app.services.user_service import UserService
from app.services.auth_service import require_admin

router = APIRouter()
svc = UserService()

@router.on_event("startup")
async def _ensure_indexes():
    await svc.ensure_indexes()

@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin)])
async def create_user(payload: UserIn):
    try:
        return await svc.create_user_admin_only(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
