# app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import get_settings

# ----- OAuth2 bearer extractor (used in dependencies) -----
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ----- Password hashing (passlib) -----
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    # bcrypt has 72-byte input limit; passlib handles safe hashing
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# ----- JWT helpers -----
def create_access_token(data: Dict[str, Any], expires_minutes: Optional[int] = None) -> str:
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
