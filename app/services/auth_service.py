# app/services/auth_service.py
from typing import Any, Dict

from fastapi import Depends, HTTPException, status
from jose import JWTError
from bson import ObjectId

from app.core.config import get_settings
from app.core.db import col_users
from app.core.security import (
    oauth2_scheme,
    verify_password,
    create_access_token,
    decode_token,
)

settings = get_settings()

# -------- main function used by /v1/auth/login --------
async def authenticate_user(email: str, password: str) -> Dict[str, Any]:
    doc = await col_users().find_one({"email": email})
    if not doc:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    if not verify_password(password, doc.get("password_hash", "")):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    user_id = str(doc.get("_id"))
    role = doc.get("role", "user")

    token = create_access_token({"sub": user_id, "role": role})
    return {
        "token": token,
        "user": {"id": user_id, "email": doc.get("email"), "role": role},
    }

# -------- FastAPI dependencies used by other routes --------
async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user id")

    doc = await col_users().find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return doc

async def require_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user
