"""The knowledge base: every .md file in kb/ is one runbook. BM25 search, no vector database needed.

A runbook can carry a "Category: password" line (several categories allowed). The runbook for the triage
category always ranks first, BM25 orders the rest. The solve node puts the top hits into the prompt.
"""
from __future__ import annotations

import re
from pathlib import Path

from rank_bm25 import BM25Okapi

KB_DIR = Path(__file__).with_name("kb")
_docs: list[dict] = []
_index: BM25Okapi | None = None


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def load() -> list[dict]:
    global _docs, _index
    _docs = []
    for p in sorted(KB_DIR.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        first = next((ln for ln in text.splitlines() if ln.strip()), p.stem)
        m = re.search(r"^Category:\s*(.+)$", text, re.M)
        cats = set(m.group(1).split()) if m else set()
        _docs.append({"title": first.lstrip("# ").strip(), "path": p.name, "text": text, "categories": cats})
    _index = BM25Okapi([_tokens(d["title"] + " " + d["text"]) for d in _docs]) if _docs else None
    return _docs


def search(query: str, k: int = 3, category: str | None = None) -> list[dict]:
    """Top k runbooks. The runbook tagged with the category comes first, then the best text matches."""
    if _index is None:
        load()
    if _index is None:
        return []
    scores = _index.get_scores(_tokens(query))
    boosted = [float(scores[i]) + (100.0 if category and category in _docs[i]["categories"] else 0.0) for i in range(len(_docs))]
    ranked = sorted(range(len(_docs)), key=lambda i: boosted[i], reverse=True)
    out = []
    for i in ranked[:k]:
        if boosted[i] <= 0:
            break
        d = {k_: v for k_, v in _docs[i].items() if k_ != "categories"}
        out.append({**d, "score": round(float(scores[i]), 2), "tagged": category in _docs[i]["categories"] if category else False})
    return out


def steps(doc: dict) -> list[str]:
    """Numbered lines of a runbook, for the fake model and for the reply."""
    return [re.sub(r"^\s*\d+[.)]\s*", "", ln).strip() for ln in doc["text"].splitlines() if re.match(r"^\s*\d+[.)]\s", ln)]
