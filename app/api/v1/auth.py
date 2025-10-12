from fastapi import APIRouter, HTTPException
from app.domain.models import LoginIn, TokenOut
from app.services.auth_service import authenticate_user

from fastapi import Form
router = APIRouter()



@router.post("/login", response_model=TokenOut)
async def login(
    username: str = Form(...),
    password: str = Form(...)
):
    # OAuth2 uses "username", but we treat it as email
    res = await authenticate_user(username, password)
    return {"access_token": res["token"], "token_type": "bearer"}


    # except HTTPException as e:
    #     raise e
    # except Exception as e:
    #     raise HTTPException(status_code=400, detail=str(e))
