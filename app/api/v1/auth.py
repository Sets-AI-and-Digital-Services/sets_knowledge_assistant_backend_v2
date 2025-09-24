from fastapi import APIRouter
from app.domain.models import LoginIn, TokenOut
from app.services.auth_service import authenticate

router = APIRouter(prefix="/sets/v1", tags=["auth"])

@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn):
    res = await authenticate(payload.email, payload.password)
    return {"access_token": res["token"], "token_type": "bearer"}
