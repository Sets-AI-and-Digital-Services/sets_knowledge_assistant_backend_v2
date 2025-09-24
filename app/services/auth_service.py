from passlib.hash import bcrypt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from bson import ObjectId
from app.core.db import col_users
from app.core.security import create_access_token, decode_token

http_bearer = HTTPBearer(auto_error=False)

async def authenticate(email: str, password: str) -> dict:
    user = await col_users().find_one({"email": email})
    if not user or not bcrypt.verify(password, user.get("password_hash", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    payload = {"sub": str(user["_id"]), "email": user["email"], "role": user.get("role", "user")}
    token = create_access_token(payload)
    return {"token": token, "user": user}

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(http_bearer)) -> dict:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    data = decode_token(credentials.credentials)
    if not data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = await col_users().find_one({"_id": ObjectId(data["sub"])})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role", "user") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user
