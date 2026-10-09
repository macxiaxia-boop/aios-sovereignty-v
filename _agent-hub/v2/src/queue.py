# v2/src/queue.py — shim re-exporting message_queue (backward compat after rename)
# Created: 2026-10-09 audit fix
# Reason: cli/aiosv2.py + 8 legacy tests still use `from src.queue import ...`
#          after message_queue rename. This shim keeps them working.

from src.message_queue import (  # noqa: F401
    ack,
    claim,
    deadletter,
    enqueue,
    get_envelope_by_id,
    list_unclaimed,
    IDEMPOTENCY_INDEX_FILE,
    IDEMPOTENCY_INDEX_LOCK,
    _read_idempotency_index_unlocked,
    _write_idempotency_index_unlocked,
    _safe_filename,
)