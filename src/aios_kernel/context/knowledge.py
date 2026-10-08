"""knowledge.py - B005 Knowledge RAG layer (Phase B).

Pydantic Document + DocumentChunk + Knowledge Protocol.

Embeddings: dev 用 hash-based 1536-dim (deterministic, no API).
Storage: sqlite + pgvector (prod). dev = sqlite JSON column.
"""
from __future__ import annotations
import hashlib
import math
import uuid
from typing import Any

from pydantic import Field

from aios_kernel.domain.envelope import Envelope


def hash_embed(text: str, dim: int = 1536) -> list[float]:
    """Deterministic hash-based 1536-dim vector."""
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
    out = []
    for i in range(dim):
        x = (seed + i * 31) % 1000
        out.append((x - 500) / 500.0)
    return out


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb > 0 else 0.0


class DocumentChunk(Envelope):
    doc_id: str
    chunk_index: int
    content: str
    token_count: int = Field(default=0)
    embedding: list[float] = Field(default_factory=list)

    def score_against(self, query_embedding: list[float]) -> float:
        return cosine(self.embedding, query_embedding)


class Document(Envelope):
    title: str
    content: str
    source_path: str | None = None
    chunks: list[DocumentChunk] = Field(default_factory=list)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into chunks by approximate token count (1 token ≈ 4 chars)."""
    char_size = chunk_size * 4
    char_overlap = overlap * 4
    chunks = []
    i = 0
    while i < len(text):
        chunk = text[i:i + char_size]
        if chunk.strip():
            chunks.append(chunk)
        i += char_size - char_overlap
        if i >= len(text):
            break
    return chunks or [text]


class Knowledge:
    """In-memory Knowledge store (dev) for B005."""

    def __init__(self):
        self._documents: dict[str, Document] = {}
        self._chunks: list[DocumentChunk] = []

    def add_document(self, title: str, content: str, source_path: str | None = None) -> Document:
        doc = Document(
            id=str(uuid.uuid4()),
            title=title,
            content=content,
            source_path=source_path,
        )
        chunks_text = chunk_text(content)
        for idx, ct in enumerate(chunks_text):
            chunk = DocumentChunk(
                id=str(uuid.uuid4()),
                doc_id=doc.id,
                chunk_index=idx,
                content=ct,
                token_count=len(ct.split()),
                embedding=hash_embed(ct),
            )
            doc.chunks.append(chunk)
            self._chunks.append(chunk)
        self._documents[doc.id] = doc
        return doc

    def retrieve(self, query: str, top_k: int = 5) -> list[tuple[DocumentChunk, float]]:
        q_emb = hash_embed(query)
        scored = [(chunk, chunk.score_against(q_emb)) for chunk in self._chunks]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


__all__ = ["Document", "DocumentChunk", "Knowledge", "hash_embed", "cosine", "chunk_text"]
