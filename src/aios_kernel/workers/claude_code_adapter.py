from __future__ import annotations

from .base import _StubAdapterBase


class ClaudeCodeAdapter(_StubAdapterBase):
    def __init__(self):
        super().__init__(worker_id="claude-code-adapter")
