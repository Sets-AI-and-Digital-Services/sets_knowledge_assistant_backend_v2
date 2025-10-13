# app/vector/faiss_store.py
from __future__ import annotations
import os, json, uuid, logging
from typing import Iterable, Any
from pathlib import Path

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Ensure .env is loaded even if this module is imported early
load_dotenv(dotenv_path=".env", override=True)
logger = logging.getLogger(__name__)


# ----- Helpers -----
def _resolve_model_name(name: str) -> str:
    """Map friendly aliases → valid Hugging Face repo IDs."""
    aliases = {
        # Embedding models
        "bge-m3": "BAAI/bge-m3",
        "bge-small-en": "BAAI/bge-small-en-v1.5",
        "bge-base-en": "BAAI/bge-base-en-v1.5",
        "m-e5-small": "intfloat/multilingual-e5-small",
        "m-e5-base": "intfloat/multilingual-e5-base",
        # Old minis
        "all-MiniLM-L6-v2": "sentence-transformers/all-MiniLM-L6-v2",
    }
    return aliases.get(name, name)


def _l2_normalize(mat: np.ndarray) -> np.ndarray:
    return mat / (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-12)


# ----- Store -----
class FaissStore:
    """
    File-backed FAISS index per session:
      ./Storage/{session_id}/faiss.index
      ./Storage/{session_id}/faiss_payload.json
      ./Storage/{session_id}/faiss_idmap.json
    """
    def __init__(self, session_dir: str, model_name: str | None = None):
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Resolve embedding model (env -> alias -> HF id)
        raw_name = model_name or os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
        resolved_name = _resolve_model_name(raw_name)
        logger.info(f"[FAISS] Using embedding model: {resolved_name} (from: {raw_name})")

        try:
            self.model = SentenceTransformer(resolved_name)
        except OSError as e:
            # Last-resort fallback to a tiny public model so app keeps running
            logger.warning(f"[FAISS] Failed to load '{resolved_name}' ({e}). Falling back to 'sentence-transformers/all-MiniLM-L6-v2'.")
            self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

        self.dim = self.model.get_sentence_embedding_dimension()

        # Files
        self.index_path   = self.session_dir / "faiss.index"
        self.payload_path = self.session_dir / "faiss_payload.json"
        self.idmap_path   = self.session_dir / "faiss_idmap.json"

        # Data
        self.index = faiss.IndexFlatIP(self.dim)  # cosine-like when normalized
        self.id_map: list[str] = []               # row -> our string id
        self.payloads: dict[str, dict[str, Any]] = {}  # id -> {text, metadata}

        # Load persisted state
        if self.index_path.exists() and self.index_path.stat().st_size > 0:
            self.index = faiss.read_index(str(self.index_path))
        if self.payload_path.exists():
            self.payloads = json.loads(self.payload_path.read_text(encoding="utf-8"))
        if self.idmap_path.exists():
            self.id_map = json.loads(self.idmap_path.read_text(encoding="utf-8"))
        else:
            # Back-compat: reconstruct id_map deterministically from payload keys
            # (JSON preserves insertion order in Python 3.7+)
            self.id_map = list(self.payloads.keys())

        # If the loaded index size mismatches our id_map, rebuild vectors now
        if self.index.ntotal != len(self.id_map) and len(self.id_map) == len(self.payloads):
            logger.warning("[FAISS] Index size != id_map size. Rebuilding vectors to realign...")
            self._rebuild_index_from_payloads()

    # ----- Persistence -----
    def _save(self) -> None:
        faiss.write_index(self.index, str(self.index_path))
        self.payload_path.write_text(json.dumps(self.payloads, ensure_ascii=False), encoding="utf-8")
        self.idmap_path.write_text(json.dumps(self.id_map, ensure_ascii=False), encoding="utf-8")

    # ----- Embedding -----
    def _embed_batch(self, texts: list[str], batch: int = 512) -> np.ndarray:
        vecs = []
        for i in range(0, len(texts), batch):
            part = self.model.encode(texts[i:i+batch], convert_to_numpy=True).astype("float32")
            vecs.append(part)
        mat = np.vstack(vecs) if vecs else np.zeros((0, self.dim), dtype="float32")
        return _l2_normalize(mat)

    def _rebuild_index_from_payloads(self) -> None:
        self.index = faiss.IndexFlatIP(self.dim)
        all_texts = [self.payloads[_id]["text"] for _id in self.id_map]
        if all_texts:
            vecs = self._embed_batch(all_texts)
            self.index.add(vecs)
        self._save()

    # ----- Public API -----
    def add(self, texts: Iterable[str], metadatas: Iterable[dict], ids: Iterable[str] | None = None) -> int:
        texts, metadatas = list(texts), list(metadatas)
        if not texts:
            return 0
        ids = list(ids or [uuid.uuid4().hex for _ in texts])

        # Detect existing ids → perform a simple, robust upsert by rebuilding
        need_rebuild = any((_id in self.payloads) for _id in ids)

        for _id, t, m in zip(ids, texts, metadatas, strict=False):
            if _id in self.payloads:
                # Update payload for upsert
                self.payloads[_id] = {"text": t, "metadata": m}
            else:
                # New
                self.payloads[_id] = {"text": t, "metadata": m}
                self.id_map.append(_id)

        if need_rebuild:
            # Re-embed everything to keep FAISS rows aligned with id_map
            self._rebuild_index_from_payloads()
        else:
            # Fast path: append only new vectors
            vecs = self._embed_batch(texts)
            if len(vecs):
                self.index.add(vecs)
            self._save()

        return len(texts)

    def search(self, query: str, top_k: int = 5, where: dict | None = None) -> list[dict[str, Any]]:
        query = (query or "").strip()
        if not query or self.index.ntotal == 0:
            return []

        q_vec = self.model.encode([query], convert_to_numpy=True).astype("float32")
        q_vec = _l2_normalize(q_vec)

        scores, idxs = self.index.search(q_vec, top_k)
        scores, idxs = scores[0], idxs[0]

        results: list[dict[str, Any]] = []
        for s, i in zip(scores, idxs):
            if i < 0 or i >= len(self.id_map):
                continue
            _id = self.id_map[i]
            payload = self.payloads.get(_id, {})
            meta = payload.get("metadata", {})
            if where and not all(meta.get(k) == v for k, v in where.items()):
                continue
            results.append({
                "content": payload.get("text", ""),
                "metadata": meta,
                "similarity_score": float(s),
            })
        return results

    def stats(self) -> dict[str, Any]:
        return {"points_count": int(self.index.ntotal)}

    def reset(self) -> None:
        self.index = faiss.IndexFlatIP(self.dim)
        self.id_map = []
        self.payloads = {}
        self._save()
