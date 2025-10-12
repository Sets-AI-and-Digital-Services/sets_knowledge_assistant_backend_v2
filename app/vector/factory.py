import os
from pathlib import Path
from app.vector.faiss_store import FaissStore
# If you keep Chroma, you can import your chroma adapter here too.

def get_vector_store(session_id: str):
    backend = os.getenv("VECTOR_BACKEND", "faiss").lower()
    model = os.getenv("EMBEDDING_MODEL", "bge-m3")
    session_dir = Path(f"./Storage/{session_id}")
    session_dir.mkdir(parents=True, exist_ok=True)

    if backend == "faiss":
        return FaissStore(session_dir=str(session_dir), model_name=model)

    # elif backend == "chroma": return ChromaStore(...)
    raise RuntimeError(f"Unknown VECTOR_BACKEND={backend}")
