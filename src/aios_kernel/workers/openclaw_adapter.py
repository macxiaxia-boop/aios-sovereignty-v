from __future__ import annotations
from .base import WorkerAdapter, _StubAdapterBase


class OpenClawAdapter(_StubAdapterBase):
    def __init__(self):
        super().__init__(worker_id="openclaw-adapter")
