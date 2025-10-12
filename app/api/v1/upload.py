# app/api/upload.py
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status, Request
from starlette.concurrency import run_in_threadpool

from app.services.auth_service import get_current_user
from app.core.upload_settings import UploadSettings

router = APIRouter(prefix="/sets/v1", tags=["upload"])
settings = UploadSettings()

SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")

def sanitize_filename(name: str) -> str:
    base = os.path.basename(name or "file").strip().replace(" ", "_")
    return SAFE_NAME.sub("", base) or "file"

async def _enforce_total_size(request: Request):
    # Reject early if Content-Length exceeds MAX_TOTAL_MB
    cl = request.headers.get("content-length")
    if cl and cl.isdigit():
        if int(cl) > settings.MAX_TOTAL_MB * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Total payload too large")

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_files(
    request: Request,
    session_id: str = Form(...),
    files: List[UploadFile] = File(...),
    user=Depends(get_current_user),
):
    await _enforce_total_size(request)

    if not files:
        raise HTTPException(400, "No files provided")
    if len(files) > settings.MAX_FILES:
        raise HTTPException(413, f"Too many files. Max {settings.MAX_FILES}")

    session_dir = Path(settings.STORAGE_ROOT) / session_id
    incoming = session_dir / "incoming"
    finaldir = session_dir / "files"
    meta_path = session_dir / "meta.json"
    incoming.mkdir(parents=True, exist_ok=True)
    finaldir.mkdir(parents=True, exist_ok=True)

    total_received = 0
    accepted = []

    for f in files:
        safe_name = sanitize_filename(f.filename or "file")
        ext = safe_name.split(".")[-1].lower() if "." in safe_name else ""
        if ext not in settings.ALLOWED_EXTS:
            raise HTTPException(415, f"Disallowed extension: .{ext}")

        mime = f.content_type or ""
        if mime not in settings.ALLOWED_MIMES:
            # allow some generic types for txt
            if not (ext == "txt" and mime in {"application/octet-stream","text/plain"}):
                raise HTTPException(415, f"Disallowed MIME: {mime}")

        tmp_path = incoming / safe_name
        sha256 = hashlib.sha256()
        written = 0
        max_bytes = settings.MAX_FILE_MB * 1024 * 1024

        with tmp_path.open("wb") as out:
            while True:
                chunk = await f.read(settings.UPLOAD_CHUNK_BYTES)
                if not chunk:
                    break
                written += len(chunk)
                total_received += len(chunk)

                if written > max_bytes:
                    out.close()
                    tmp_path.unlink(missing_ok=True)
                    raise HTTPException(413, f"{safe_name} exceeds {settings.MAX_FILE_MB} MB")

                if total_received > settings.MAX_TOTAL_MB * 1024 * 1024:
                    out.close()
                    tmp_path.unlink(missing_ok=True)
                    raise HTTPException(413, f"Total upload exceeds {settings.MAX_TOTAL_MB} MB")

                sha256.update(chunk)
                out.write(chunk)

        file_hash = sha256.hexdigest()

        # Dedup inside this session (compare against sidecar .sha256 files)
        duplicate = False
        for existing_name in os.listdir(finaldir):
            hpath = finaldir / f".{existing_name}.sha256"
            if hpath.exists() and hpath.read_text() == file_hash:
                duplicate = True
                break

        if duplicate:
            tmp_path.unlink(missing_ok=True)
            # you can switch to 'continue' to silently ignore duplicates
            raise HTTPException(409, f"Duplicate file: {safe_name}")

        final_path = finaldir / safe_name
        await run_in_threadpool(shutil.move, str(tmp_path), str(final_path))
        (finaldir / f".{safe_name}.sha256").write_text(file_hash)

        accepted.append({
            "filename": safe_name,
            "hash": file_hash,
            "size": written,
            "mime": mime,
        })

    # atomically update meta.json
    existing = []
    if meta_path.exists():
        try:
            existing = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            existing = []
    existing.extend(accepted)
    tmp = tempfile.NamedTemporaryFile("w", delete=False, dir=session_dir)
    try:
        json.dump(existing, tmp, ensure_ascii=False)
        tmp.flush(); os.fsync(tmp.fileno())
        tmp.close()
        shutil.move(tmp.name, meta_path)
    finally:
        try: os.unlink(tmp.name)
        except FileNotFoundError: pass

    return {
        "message": "Files uploaded",
        "accepted_count": len(accepted),
        "total_received_bytes": total_received,
        "files": accepted,
        "limits": {
            "max_files": settings.MAX_FILES,
            "max_file_mb": settings.MAX_FILE_MB,
            "max_total_mb": settings.MAX_TOTAL_MB,
        }
    }
