# app/api/v1/stats.py
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Body, HTTPException, Query, status
from pydantic import BaseModel, Field

# Optional helpers; endpoint works without them
try:
    from app.core.dependencies import get_rag_system, check_uploaded_files_exist  # noqa: F401
except Exception:  # pragma: no cover
    get_rag_system = None  # type: ignore
    check_uploaded_files_exist = None  # type: ignore

# Vector store stats (for chunks_total)
from app.vector.factory import get_vector_store

router = APIRouter()

# ---------- Schemas ----------
class StatsIn(BaseModel):
    session_id: str

class FileStat(BaseModel):
    filename: str
    size_bytes: int

class SessionStatsOut(BaseModel):
    session_id: str = Field(..., description="Session UUID")
    files_total: int
    files: List[FileStat]
    chunks_total: int
    chunks_by_file: Dict[str, int] = Field(default_factory=dict)
    message: str = "OK"

# ---------- Internal helpers ----------
DOC_EXTS = {".pdf", ".docx", ".pptx", ".txt", ".csv", ".md", ".html", ".xlsx"}  # extend as needed
SIDE_EXTS = {".sha256"}
SIDE_FILENAMES = {"meta.json"}
FILES_SUBDIRS = ["", "files", "uploads"]  # common subfolders used by uploaders

def _session_dir(session_id: str) -> Path:
    return Path("./Storage") / session_id

def _load_meta(session_id: str) -> Optional[object]:
    """
    Read upload meta if available.
    Return the raw JSON (can be dict OR list) and let the parser handle shapes.
    """
    path = _session_dir(session_id) / "meta.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None

def _files_from_meta(session_id: str, meta: object) -> List[FileStat]:
    """
    Build FileStat list from meta.json.

    Accepted shapes:
      1) list[dict]  e.g. [{"original_name": "...", "saved_name": "...", "size_bytes": 123}, ...]
      2) list[str]   e.g. ["A.pdf", "B.docx"]
      3) dict with one of: "files" | "uploads" | "items" -> list[dict|str]
    """
    # Normalize to a list of items
    if isinstance(meta, list):
        items = meta
    elif isinstance(meta, dict):
        items = meta.get("files") or meta.get("uploads") or meta.get("items") or []
    else:
        items = []

    out: List[FileStat] = []
    for it in items:
        if isinstance(it, str):
            original = it
            saved = it
            size = 0
        elif isinstance(it, dict):
            original = it.get("original_name") or it.get("filename") or it.get("name") or it.get("original") or it.get("file")
            saved = it.get("saved_name") or it.get("saved") or it.get("storage_name") or it.get("path") or original
            size = it.get("size_bytes") or it.get("size") or it.get("filesize") or 0
        else:
            continue  # unknown entry shape

        # If we still don't have a size, try to stat the saved file on disk
        if (not size) and saved:
            stat = _stat_file_if_exists(session_id, str(saved))
            if stat:
                _, size = stat

        if original:
            out.append(FileStat(filename=str(original), size_bytes=int(size or 0)))

    return out

def _stat_file_if_exists(session_id: str, saved_name: str) -> Optional[Tuple[str, int]]:
    """Try to locate a saved file in common subdirs and return (name, size)."""
    for sub in FILES_SUBDIRS:
        root = _session_dir(session_id) / sub if sub else _session_dir(session_id)
        p = root / saved_name
        if p.exists() and p.is_file():
            return (p.name, p.stat().st_size)
    return None


def _files_from_fs(session_id: str) -> List[FileStat]:
    """Scan common subdirs for primary docs, exclude sidecars & unknowns (unless you remove DOC_EXTS check)."""
    out: List[FileStat] = []
    for sub in FILES_SUBDIRS:
        root = _session_dir(session_id) / sub if sub else _session_dir(session_id)
        if not root.exists():
            continue
        for p in root.iterdir():
            if not p.is_file():
                continue
            if p.name.startswith("."):
                continue
            if p.name in SIDE_FILENAMES:
                continue
            if p.suffix.lower() in SIDE_EXTS:
                continue
            if DOC_EXTS and p.suffix.lower() not in DOC_EXTS:
                continue
            out.append(FileStat(filename=p.name, size_bytes=p.stat().st_size))
    return out

def _load_faiss_payload(session_id: str) -> Optional[dict]:
    """Read FAISS payload (id -> {text, metadata}) if present."""
    path = _session_dir(session_id) / "faiss_payload.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None

def _count_chunks_by_file_from_payload(payload: dict) -> Dict[str, int]:
    """Count chunks by metadata.filename (if available)."""
    counter: Counter[str] = Counter()
    for entry in payload.values():
        md = (entry or {}).get("metadata", {})
        fn = md.get("filename")
        if fn:
            counter[fn] += 1
        else:
            counter["_unknown_"] += 1
    return dict(counter)

# ---------- Endpoint ----------
@router.post("/summary", response_model=SessionStatsOut, status_code=status.HTTP_200_OK)
async def get_session_stats(
    session_id_q: Optional[str] = Query(default=None, alias="session_id"),
    body: Optional[StatsIn] = Body(default=None),
) -> SessionStatsOut:
    """
    Return total uploaded documents and total/generated chunks for a given session.
    Accepts session_id via query or JSON body.
    """
    session_id = session_id_q or (body.session_id if body else None)
    if not session_id:
        raise HTTPException(status_code=422, detail="session_id is required (query or body)")

    folder = _session_dir(session_id)
    if not folder.exists():
        raise HTTPException(status_code=404, detail="Invalid session_id or no uploads for this session")

    # 1) Files: meta.json → filesystem → payload fallback
    meta = _load_meta(session_id)
    if meta:
        files_stats = _files_from_meta(session_id, meta)
    else:
        files_stats = _files_from_fs(session_id)

    payload = _load_faiss_payload(session_id)
    chunks_by_file: Dict[str, int] = _count_chunks_by_file_from_payload(payload) if payload else {}

    if not files_stats and chunks_by_file:
        # Derive at least file names from payload when originals/meta are gone
        files_stats = [
            FileStat(filename=name, size_bytes=0)
            for name in sorted(chunks_by_file.keys())
            if name != "_unknown_"
        ]

    # 2) Chunks total: vector store stats (authoritative), fallback to payload sum
    try:
        vs = get_vector_store(session_id)
        vs_stats = vs.stats()  # {"points_count": int}
        chunks_total = int(vs_stats.get("points_count", 0))
    except Exception:
        chunks_total = sum(chunks_by_file.values()) if chunks_by_file else 0

    return SessionStatsOut(
        session_id=session_id,
        files_total=len(files_stats),
        files=files_stats,
        chunks_total=chunks_total,
        chunks_by_file=chunks_by_file,
        message="Stats generated successfully" if files_stats or chunks_total else "No data for session",
    )
