"""repository.py — Async SQLAlchemy session factory + protocol.

A Repository is a thin async wrapper around an AsyncSession. The
default implementation talks to SQLite (via aiosqlite) so the kernel can
boot in dev/CI without a real Postgres; production swaps the URL.

This module is the ONLY place that knows about SQLAlchemy. The domain
services take a Repository instance and call repo.add(obj),
repo.commit(), repo.refresh(obj). They never see an
AsyncSession directly.

Why a Protocol (not a concrete class)?
- Services are unit-tested with an in-memory InMemoryRepository
  (tests do not need a real DB).
- The real SqlAlchemyRepository is a single class bound to a
  session factory.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Protocol

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


# Default URL: local SQLite. Override with AIOS_KERNEL_DATABASE_URL.
def default_database_url():
    return os.environ.get("AIOS_KERNEL_DATABASE_URL", "sqlite+aiosqlite:///aios_kernel.db")


def make_engine(url=None, echo=False):
    """Build the async SQLAlchemy engine.

    For SQLite: sqlite+aiosqlite:///aios_kernel.db (relative path).
    For Postgres (prod): postgresql+psycopg://user:pass@host:5432/db.
    """
    return create_async_engine(url or default_database_url(), echo=echo, future=True)


def make_session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def session_scope(factory):
    """Yield a session, commit on success, rollback on error."""
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------- Repository protocol ----------------------------------------------


class Repository(Protocol):
    """Thin async persistence facade used by domain services.

    Concrete impls: SqlAlchemyRepository (real DB) and
    InMemoryRepository (tests). Services depend on this protocol only.
    """

    async def add(self, obj):
        ...

    async def commit(self):
        ...

    async def refresh(self, obj):
        ...

    async def get(self, model, pk):
        ...

    async def delete(self, obj):
        ...

    async def flush(self):
        ...

    async def find(self, model, **filters):
        """Filter lookup. Returns a list of ORM/Pydantic rows.

        ``limit`` is honoured when supplied (int). Other keyword
        arguments are matched as ``column == value``. The semantics of
        what's returned depends on the concrete impl (Pydantic for the
        in-memory store, ORM rows for the SQL impl).
        """
        ...


# ---------- In-memory repository for unit tests ------------------------------


class InMemoryRepository:
    """In-process dict-backed repository; used by unit tests.

    add accepts any Pydantic domain object. get looks up by id
    (string form, as emitted by Envelope). commit is a no-op.
    """

    def __init__(self):
        self._store = {}
        self.events = []  # for assertions

    async def add(self, obj):
        bucket = self._store.setdefault(type(obj), {})
        bucket[obj.id] = obj
        self.events.append(("add", obj))

    async def commit(self):
        self.events.append(("commit", None))

    async def refresh(self, obj):
        return None

    async def get(self, model, pk):
        return self._store.get(model, {}).get(pk)

    async def delete(self, obj):
        bucket = self._store.get(type(obj), {})
        bucket.pop(obj.id, None)
        self.events.append(("delete", obj))

    async def flush(self):
        return None

    async def find(self, model, **filters):
        """In-memory equality filter.

        Mirrors SqlAlchemyRepository.find semantics for unit tests.
        Returns the stored Pydantic objects (not ORM rows).
        """
        bucket = self._store.get(model, {})
        results = []
        limit = filters.pop("limit", None)
        for obj in bucket.values():
            match = True
            for key, value in filters.items():
                if not hasattr(obj, key):
                    match = False
                    break
                attr = getattr(obj, key)
                attr_value = attr.value if hasattr(attr, "value") else attr
                if attr_value != value:
                    match = False
                    break
            if match:
                results.append(obj)
        if limit is not None:
            results = results[: int(limit)]
        return results

    def all(self, model):
        return list(self._store.get(model, {}).values())

    def clear(self):
        self._store.clear()
        self.events.clear()


__all__ = [
    "Repository",
    "InMemoryRepository",
    "default_database_url",
    "make_engine",
    "make_session_factory",
    "session_scope",
]