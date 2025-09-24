from datetime import datetime
from passlib.hash import bcrypt
from app.core.db import col_users
from app.domain.models import UserIn, UserOut

class UserService:
    def __init__(self):
        self.col = col_users()

    async def ensure_indexes(self):
        await self.col.create_index("email", unique=True)

    async def create_user_admin_only(self, payload: UserIn, role: str = "user") -> UserOut:
        if await self.col.find_one({"email": payload.email}):
            raise ValueError("Email already registered")
        doc = {
            "name": payload.name,
            "email": payload.email,
            "password_hash": bcrypt.hash(payload.password),
            "role": role,  # default: normal user
            "created_at": datetime.utcnow(),
        }
        res = await self.col.insert_one(doc)
        return UserOut(
            id=str(res.inserted_id),
            name=doc["name"],
            email=doc["email"],
            role=doc["role"],
            created_at=doc["created_at"],
        )
