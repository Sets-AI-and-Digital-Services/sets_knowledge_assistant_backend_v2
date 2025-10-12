# app/core/dependencies.py
from __future__ import annotations
import os
from pathlib import Path
from typing import Iterable, List, Dict, Any

from fastapi import HTTPException

# loaders
import fitz  # PyMuPDF
from docx import Document as DocxDocument

# vector store (factory)
try:
    from app.vector.factory import get_vector_store
except ImportError:
    # fallback: if you haven't added app/vector yet and still use Chroma directly,
    # you can stub this to your existing Chroma constructor.
    def get_vector_store(session_id: str):
        raise RuntimeError(
            "Vector factory not found. Add app/vector/factory.py or switch your code to use your existing Chroma store."
        )

# -------------------------
# Helpers
# -------------------------

def _session_dir(session_id: str) -> Path:
    return Path("./Storage") / session_id

def _files_dir(session_id: str) -> Path:
    return _session_dir(session_id) / "files"

def check_uploaded_files_exist(session_id: str, rag: Any | None = None) -> None:
    """Ensure the user has uploaded at least one file for this session."""
    fdir = _files_dir(session_id)
    if not fdir.exists() or not any(p.is_file() for p in fdir.iterdir()):
        raise HTTPException(status_code=400, detail="Please upload files first.")

# -------------------------
# Minimal text extractors
# -------------------------

def _read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def _read_docx(path: Path) -> str:
    doc = DocxDocument(path)
    return "\n".join(p.text for p in doc.paragraphs)

def _read_pdf(path: Path) -> str:
    out = []
    with fitz.open(path) as doc:
        for page in doc:
            out.append(page.get_text("text"))
    return "\n".join(out)

def _extract_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in {".txt", ".csv", ".json", ".xml"}:  # simple
        return _read_txt(path)
    if ext in {".docx"}:
        return _read_docx(path)
    if ext in {".pdf"}:
        return _read_pdf(path)
    # unsupported here → return empty (or add more loaders if you like)
    return ""

def _chunk(text: str, size: int = 900, overlap: int = 150) -> List[str]:
    if not text:
        return []
    chunks = []
    i = 0
    n = len(text)
    while i < n:
        chunks.append(text[i : i + size])
        i += max(1, size - overlap)
    return chunks

# -------------------------
# Simple RAG wrapper class
# -------------------------

class SimpleRAG:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.store = get_vector_store(session_id)

    def build_index(self, force_rebuild: bool = False):
        """
        Build/refresh per-session index from files in ./Storage/{session_id}/files.
        For simplicity, we reset before indexing to avoid duplicates.
        """
        files_dir = _files_dir(self.session_id)
        if not files_dir.exists():
            return

        if force_rebuild:
            try:
                self.store.reset()
            except Exception:
                pass
        else:
            # simple policy: reset each time for now, so you don't accumulate duplicates
            try:
                self.store.reset()
            except Exception:
                pass

        for p in files_dir.iterdir():
            if not p.is_file():
                continue
            text = _extract_text(p)
            if not text.strip():
                continue
            chunks = _chunk(text)
            # prepare metadata per chunk
            metas = []
            ids = []
            for idx, _ in enumerate(chunks):
                metas.append({"filename": p.name, "chunk_index": idx})
                ids.append(f"{p.name}:{idx}")
            # add to vector store
            self.store.add(chunks, metas, ids)

    def get_collection_stats(self) -> Dict[str, Any]:
        try:
            return self.store.stats()
        except Exception:
            return {"points_count": 0}

    def query(self, question: str) -> Dict[str, Any]:
        hits = self.store.search(question, top_k=int(os.getenv("TOP_K", 5)))
        # You can wire Gemini here; for now, return a simple answer using the top hit.
        summary = hits[0]["content"][:500] if hits else "لم أجد إجابة مؤكدة في المستندات."
        return {"answer": summary, "sources": hits}

# -------------------------
# Factory function used by your routes
# -------------------------

def get_rag_system(session_id: str) -> SimpleRAG:
    return SimpleRAG(session_id=session_id)
