import re
_WORD = re.compile(r"\w+", re.UNICODE)

def _terms(text: str) -> set[str]:
    return set(_WORD.findall((text or "").lower()))

def extractive_summarize(question: str, docs: list[dict]) -> str:
    q_terms = _terms(question)
    picked: list[str] = []
    for h in docs:
        content = h.get("content") or ""
        sents = re.split(r"(?<=[\.!\?؟])\s+", content)
        if not sents:
            continue
        scored = sorted(sents, key=lambda s: len(q_terms & _terms(s)), reverse=True)
        picked.extend([s for s in scored[:2] if s])
        if len(picked) >= 10:
            break
    text = " ".join(picked[:8]).strip()
    return text or (docs[0].get("content") or "")[:800]
