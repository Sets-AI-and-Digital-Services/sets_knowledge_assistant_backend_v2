# app/api/query.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.core.dependencies import get_rag_system, check_uploaded_files_exist
from app.services.auth_service import get_current_user

class AskIn(BaseModel):
    session_id: str
    query: str

router = APIRouter(prefix="/sets/v1", tags=["query"])

@router.post("/query")
async def ask(payload: AskIn, user=Depends(get_current_user)):
    rag = get_rag_system(payload.session_id)
    check_uploaded_files_exist(payload.session_id, rag=rag)
    result = rag.query(payload.query)
    return result
