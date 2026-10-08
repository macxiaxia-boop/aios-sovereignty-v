"""run_verifier.py - Verifier standalone process launcher (T0035 Section 2).

Boots the Verifier FastAPI server in a SEPARATE OS process (so the
Verifier's PID differs from the Kernel's). The Kernel talks to it over
HTTP at VERIFIER_HOST:VERIFIER_PORT (default 127.0.0.1:9001).

Usage:
    python scripts/run_verifier.py            # foreground, port 9001
    python scripts/run_verifier.py --port 9999

Environment:
    VERIFIER_HOST (default 127.0.0.1)
    VERIFIER_PORT (default 9001)
    VERIFIER_ID   (default "deterministic-verifier")
    AIOS_DATABASE_URL (SQLAlchemy URL for EvidenceStore; only used by
                       SqlAlchemyEvidenceStore - Phase A uses
                       InMemoryEvidenceStore by default)

The bash wrapper (scripts/run_verifier.sh) exec()s this script.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

# Make `src/` importable when run as a script without installation.
_THIS = os.path.dirname(os.path.abspath(__file__))
_KERNEL = os.path.dirname(_THIS)
_SRC = os.path.join(_KERNEL, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


def main() -> int:
    parser = argparse.ArgumentParser(description="AIOS Verifier (T0035) standalone process")
    parser.add_argument("--host", default=os.environ.get("VERIFIER_HOST", "127.0.0.1"))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("VERIFIER_PORT", "9001")),
    )
    parser.add_argument(
        "--verifier-id",
        default=os.environ.get("VERIFIER_ID", "deterministic-verifier"),
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("VERIFIER_LOG_LEVEL", "info"),
    )
    args = parser.parse_args()

    # Import after sys.path mutation (so `aios_kernel` resolves).
    import uvicorn

    from aios_kernel.verifier.server import create_app

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    log = logging.getLogger("run_verifier")
    log.info("starting AIOS Verifier on %s:%d (pid=%d, verifier_id=%s)",
             args.host, args.port, os.getpid(), args.verifier_id)

    # Force the requested values into the environment so create_app()
    # picks them up (it reads os.environ defaults).
    os.environ["VERIFIER_HOST"] = args.host
    os.environ["VERIFIER_PORT"] = str(args.port)
    os.environ["VERIFIER_ID"] = args.verifier_id

    app = create_app(verifier_id=args.verifier_id)
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level)
    return 0


if __name__ == "__main__":
    sys.exit(main())
