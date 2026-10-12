from __future__ import annotations

from .base import _StubAdapterBase


class HermesAdapter(_StubAdapterBase):
    def __init__(self):
        super().__init__(worker_id="hermes-adapter")
