import os, requests

def local_llm_grounded_synthesis(question: str, docs: list[dict], fallback_text: str) -> str:
    model = os.getenv("OLLAMA_MODEL", "llama3.1:8b-instruct")
    ctx = "\n\n---\n\n".join(f"[{i+1}] {(d.get('content') or '')}" for i, d in enumerate(docs))
    prompt = (
        "Answer the question using ONLY the context. Cite like [1], [2]. "
        "If unsure, say you don't know.\n\n"
        f"Question:\n{question}\n\nContext:\n{ctx}\n"
    )
    try:
        r = requests.post("http://localhost:11434/api/generate",
                          json={"model": model, "prompt": prompt, "stream": False}, timeout=60)
        if r.ok:
            out = (r.json() or {}).get("response", "").strip()
            return out or fallback_text
    except Exception:
        pass
    return fallback_text
