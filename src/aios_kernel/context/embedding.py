"""embedding.py - Phase B B005 Knowledge RAG: hash-based embedding (dev placeholder).

In dev/CI we do NOT call any external API (no OpenAI/Cohere). The hash-based
embedder is fully deterministic, offline, and produces a 1536-dim unit
vector for any input string. The "trick" that makes it work for retrieval
is that we tokenise the text first, hash each token to a deterministic
unit vector, then sum + re-normalise. Two texts that share tokens will
have non-zero cosine similarity (proportional to the number of shared
tokens) -- which is exactly the property retrieval needs.

In production the same KnowledgeService interface accepts any object
implementing the Embedder protocol; a real OpenAI/Cohere embedder can
replace HashEmbedding with no other code change.

Public surface:
  - EMBEDDING_DIM: int = 1536
  - Embedder: Protocol
  - HashEmbedding: deterministic dev impl
  - cosine_similarity(a, b) -> float  (numpy, in [-1, 1])
  - cosine_top_k(query_vec, candidates, top_k) -> list[(idx, score)]
"""
from __future__ import annotations

import hashlib
import math
from typing import Iterable, Protocol, Sequence

import numpy as np

# Standard OpenAI text-embedding-ada-002 dim. We keep it constant so the
# downstream code never has to special-case dev vs prod.
EMBEDDING_DIM: int = 1536


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class Embedder(Protocol):
    """Embedding backend contract used by KnowledgeService.retrieve().

    The default implementation is HashEmbedding (deterministic, no network).
    A production OpenAI/Cohere embedder plugs in here without any other
    change to the knowledge layer.
    """

    model_id: str
    dim: int

    def embed(self, text: str) -> list[float]:
        """Return a unit vector of length `dim` representing the text."""
        ...

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        """Default: one embed() call per text. Subclasses may optimise."""
        ...


# ---------------------------------------------------------------------------
# Hash-based deterministic embedder (dev placeholder)
# ---------------------------------------------------------------------------


def _tokenise(text: str) -> list[str]:
    """Lower-cased, whitespace-split, alpha-numeric tokens (>=2 chars).

    Same approach as B004's WordTokenizer so the dev embedding is
    consistent with the compiler's token counting.
    """
    if not text:
        return []
    out: list[str] = []
    for raw in text.lower().split():
        # Keep word characters only (cheap normalisation).
        tok = "".join(ch for ch in raw if ch.isalnum())
        if len(tok) >= 2:
            out.append(tok)
    return out


def _seeded_unit_vector(token: str, dim: int = EMBEDDING_DIM) -> np.ndarray:
    """Map a single token to a deterministic unit vector.

    SHA-256 of the token is used to seed a numpy RNG; the first `dim`
    standard-normal samples form the raw vector, which is then L2-normalised.
    Two different tokens map to two independent random unit vectors, so
    the dot product between them is ~0 on average.
    """
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    seed = int.from_bytes(digest[:8], "big")
    rng = np.random.default_rng(seed)
    vec = rng.standard_normal(dim).astype(np.float32)
    norm = float(np.linalg.norm(vec))
    if norm == 0.0:
        return vec
    return vec / norm


class HashEmbedding:
    """Bag-of-words hash embedder.

    The embed() function tokenises the text, maps each token to a
    deterministic unit vector, sums them, and re-normalises. The result
    is a unit vector in R^{EMBEDDING_DIM}. Two texts with overlapping
    vocab will have non-zero cosine similarity (proportional to the
    overlap). Two texts with disjoint vocab will be near-orthogonal.

    Properties:
      - deterministic (same text -> same vector, across processes/machines)
      - offline (no network, no API key)
      - no env dependency (OPENAI_API_KEY is intentionally not consulted)
      - O(N_tokens) per embed; N_tokens ~ number of whitespace-separated
        words after stripping punctuation.
    """

    model_id: str = "hash-dev-1536"
    dim: int = EMBEDDING_DIM

    def __init__(self, dim: int = EMBEDDING_DIM) -> None:
        if dim <= 0:
            raise ValueError(f"dim must be positive, got {dim}")
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        tokens = _tokenise(text)
        if not tokens:
            return [0.0] * self.dim
        # Sum token vectors.
        vec = np.zeros(self.dim, dtype=np.float32)
        for tok in tokens:
            vec += _seeded_unit_vector(tok, self.dim)
        # L2 normalise.
        norm = float(np.linalg.norm(vec))
        if norm == 0.0:
            return [0.0] * self.dim
        vec = vec / norm
        return vec.tolist()

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


# ---------------------------------------------------------------------------
# Cosine similarity helpers (numpy, dev)
# ---------------------------------------------------------------------------


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity of two equal-length vectors in [-1, 1].

    Returns 0.0 if either vector is the zero vector. The function is
    defensive: a length mismatch raises ValueError because the caller
    almost certainly made a mistake (e.g. mixed dimensions).
    """
    if len(a) != len(b):
        raise ValueError(
            f"cosine_similarity: length mismatch a={len(a)} b={len(b)}"
        )
    va = np.asarray(a, dtype=np.float32)
    vb = np.asarray(b, dtype=np.float32)
    na = float(np.linalg.norm(va))
    nb = float(np.linalg.norm(vb))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


def cosine_top_k(
    query_vec: Sequence[float],
    candidates: Sequence[Sequence[float]],
    top_k: int,
) -> list[tuple[int, float]]:
    """Return the top-k (index, score) pairs by cosine similarity.

    `candidates[i]` is the i-th candidate vector. The function is O(N)
    which is fine for dev (sqlite + numpy) but obviously not for
    production. In production this becomes a pgvector index scan.

    Returns at most `top_k` entries, sorted by score descending. If
    `len(candidates) < top_k` all candidates are returned. If two
    candidates have equal score, the lower index wins (stable order).
    """
    if top_k <= 0:
        return []
    if not candidates:
        return []
    q = np.asarray(query_vec, dtype=np.float32)
    qn = float(np.linalg.norm(q))
    if qn == 0.0:
        return []
    q = q / qn

    scores: list[tuple[int, float]] = []
    for i, c in enumerate(candidates):
        v = np.asarray(c, dtype=np.float32)
        vn = float(np.linalg.norm(v))
        if vn == 0.0:
            continue
        s = float(np.dot(q, v / vn))
        scores.append((i, s))

    # Partial sort: descending by score; stable on equal score (lower idx first).
    scores.sort(key=lambda t: (-t[1], t[0]))
    return scores[:top_k]


__all__ = [
    "EMBEDDING_DIM",
    "Embedder",
    "HashEmbedding",
    "cosine_similarity",
    "cosine_top_k",
    "_tokenise",
    "_seeded_unit_vector",
]
