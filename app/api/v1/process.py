# app/api/process.py
from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import get_rag_system, check_uploaded_files_exist
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/sets/v1", tags=["process"])

@router.post("/process")
async def process_documents(session_id: str, user=Depends(get_current_user)):
    rag = get_rag_system(session_id)
    check_uploaded_files_exist(session_id, rag=rag)  # guard: must upload first
    rag.build_index(force_rebuild=False)
    stats = rag.get_collection_stats()
    return {"message": "Processed", "stats": stats}
