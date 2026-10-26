"""Diary retrieval for the mind's prompt.

Embedding model: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 through fastembed
(ONNX, CPU, 384-d, ~220 MB download once to the fastembed cache). Chosen because it runs locally
with no API key and puts Chinese and English sentences in one space (the owner talks in Chinese,
the diary may be English). If fastembed or the model is unavailable, a hashed character n-gram
vector is used instead and the vector is tagged "hash" so the two are never compared.
"""
from __future__ import annotations

import datetime as dt
import hashlib
from functools import lru_cache

import numpy as np

from . import state as S

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
HASH_DIM = 512


@lru_cache(maxsize=1)
def _model():
    try:
        from fastembed import TextEmbedding
        return TextEmbedding(MODEL_NAME)
    except Exception:  # noqa: BLE001  (no package, no network for the first download, ...)
        return None


def _hash_vec(text: str) -> np.ndarray:
    v = np.zeros(HASH_DIM, dtype=np.float32)
    t = f"  {text.lower()}  "
    for n in (2, 3):
        for i in range(len(t) - n + 1):
            h = int(hashlib.md5(t[i:i + n].encode()).hexdigest()[:8], 16)
            v[h % HASH_DIM] += 1.0
    return v


def embed(texts: list[str], force_hash: bool = False) -> tuple[np.ndarray, str]:
    m = None if force_hash else _model()
    if m is not None:
        arr, kind = np.array(list(m.embed(texts)), dtype=np.float32), MODEL_NAME
    else:
        arr, kind = np.stack([_hash_vec(t) for t in texts]), "hash"
    arr /= np.linalg.norm(arr, axis=1, keepdims=True) + 1e-9
    return arr, kind


def embed_diary(entries: list[dict], force_hash: bool = False) -> list[dict]:
    """Fill missing embeddings in place: entry['embedding'] = {'model', 'vector'}."""
    todo = [e for e in entries if not e.get("embedding")]
    if todo:
        vecs, kind = embed([e["text"] for e in todo], force_hash)
        for e, v in zip(todo, vecs):
            e["embedding"] = {"model": kind, "vector": [round(float(x), 5) for x in v]}
    return entries


def retrieve(query: str, k: int = 5, entries: list[dict] | None = None, *, recency_half_life_days: float = 0.0,
             force_hash: bool = False) -> list[dict]:
    """Top-k diary entries by cosine similarity to `query` (optionally boosted toward recent ones).
    Reads pet/state/diary.jsonl when `entries` is None and writes back any new embeddings."""
    own = entries is None
    entries = S.load_diary() if own else entries
    if not entries:
        return []
    embed_diary(entries, force_hash)
    if own:
        S.save_diary(entries)
    qv, kind = embed([query], force_hash)
    pool = [e for e in entries if e["embedding"]["model"] == kind]
    if not pool:
        return []
    m = np.array([e["embedding"]["vector"] for e in pool], dtype=np.float32)
    scores = m @ qv[0]
    if recency_half_life_days > 0:
        ts = [e["t"][:10] for e in pool]
        newest = max(ts)
        age = np.array([(dt.date.fromisoformat(newest) - dt.date.fromisoformat(t)).days for t in ts], dtype=np.float32)
        scores = scores * np.power(0.5, age / recency_half_life_days)
    order = np.argsort(-scores)[:k]
    return [{"t": pool[i]["t"], "text": pool[i]["text"], "tags": pool[i].get("tags", []),
             "score": round(float(scores[i]), 3)} for i in order]
