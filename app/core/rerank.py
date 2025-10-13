import os
from sentence_transformers import CrossEncoder

_RERANKER = None

def _get_reranker():
    global _RERANKER
    if _RERANKER is None:
        model_name = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-2-v2")
        _RERANKER = CrossEncoder(model_name)
    return _RERANKER

def cross_encoder_rerank(query: str, hits: list[dict]) -> list[dict]:
    if not hits:
        return hits
    reranker = _get_reranker()
    pairs = [(query, h["content"]) for h in hits]
    scores = reranker.predict(pairs).tolist()
    out = []
    for h, s in zip(hits, scores):
        h2 = dict(h)
        h2["rerank_score"] = float(s)
        out.append(h2)
    out.sort(key=lambda x: x["rerank_score"], reverse=True)
    return out
