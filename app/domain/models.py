from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime
from typing import Literal

class UserIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6)

class UserOut(BaseModel):
    model_config = ConfigDict(extra="ignore")  # ignore legacy extras if any
    id: str
    name: str
    email: EmailStr
    role: Literal["admin", "user"] = "user"
    created_at: datetime

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
