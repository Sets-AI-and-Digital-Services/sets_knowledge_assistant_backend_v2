# app/api/sessions.py
from fastapi import APIRouter, Depends, status
from uuid import uuid4
from datetime import datetime
from app.core.db import col_sessions
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/sets/v1", tags=["sessions"])

@router.post("/create_session_id", status_code=status.HTTP_201_CREATED)
async def create_session_id(user=Depends(get_current_user)):
    session_id = uuid4().hex
    await col_sessions().insert_one({
        "session_id": session_id,
        "user_id": str(user["_id"]),
        "created_at": datetime.utcnow(),
        "status": "new"
    })
    return {"session_id": session_id}
