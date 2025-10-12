from __future__ import annotations
import json, os, uuid
from typing import Iterable, Any
from pathlib import Path
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

class FaissStore:
    """
    File-backed FAISS index per session:
      ./Storage/{session_id}/faiss.index
      ./Storage/{session_id}/faiss_payload.json
    """
    def __init__(self, session_dir: str, model_name: str = "all-MiniLM-L6-v2"):
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.dim = self.model.get_sentence_embedding_dimension()

        self.index_path = self.session_dir / "faiss.index"
        self.payload_path = self.session_dir / "faiss_payload.json"

        self.index = faiss.IndexFlatIP(self.dim)  # cosine if we normalize
        self.id_map: list[str] = []
        self.payloads: dict[str, dict[str, Any]] = {}

        if self.index_path.exists() and self.index_path.stat().st_size > 0:
            self.index = faiss.read_index(str(self.index_path))
        if self.payload_path.exists():
            self.payloads = json.loads(self.payload_path.read_text(encoding="utf-8"))
            self.id_map = list(self.payloads.keys())

    def _save(self):
        faiss.write_index(self.index, str(self.index_path))
        self.payload_path.write_text(json.dumps(self.payloads, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _normalize(x: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(x, axis=1, keepdims=True) + 1e-12
        return x / norms

    def add(self, texts: Iterable[str], metadatas: Iterable[dict], ids: Iterable[str] | None = None) -> int:
        texts, metadatas = list(texts), list(metadatas)
        if not texts:
            return 0
        ids = list(ids or [uuid.uuid4().hex for _ in texts])
        vecs = self.model.encode(texts, convert_to_numpy=True).astype("float32")
        vecs = self._normalize(vecs)
        self.index.add(vecs)
        for _id, t, m in zip(ids, texts, metadatas, strict=False):
            self.payloads[_id] = {"text": t, "metadata": m}
            self.id_map.append(_id)
        self._save()
        return len(texts)

    def search(self, query: str, top_k: int = 5, where: dict | None = None) -> list[dict[str, Any]]:
        if not query.strip() or self.index.ntotal == 0:
            return []
        q = self.model.encode([query], convert_to_numpy=True).astype("float32")
        q = self._normalize(q)
        scores, idxs = self.index.search(q, top_k)
        scores, idxs = scores[0], idxs[0]
        out = []
        for s, i in zip(scores, idxs):
            if i < 0 or i >= len(self.id_map):
                continue
            _id = self.id_map[i]
            payload = self.payloads.get(_id, {})
            meta = payload.get("metadata", {})
            if where and not all(meta.get(k) == v for k, v in where.items()):
                continue
            out.append({"content": payload.get("text", ""), "metadata": meta, "similarity_score": float(s)})
        return out

    def stats(self) -> dict[str, Any]:
        return {"points_count": int(self.index.ntotal)}

    def reset(self) -> None:
        self.index = faiss.IndexFlatIP(self.dim)
        self.id_map = []
        self.payloads = {}
        self._save()
