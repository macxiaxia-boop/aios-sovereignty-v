#!/usr/bin/env python3
# v2/src/start_consumer_real.py — start v2_consumer with REAL claude -p adapter
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Ensure src package import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import v2_consumer
from src.claude_adapter import _claude_dispatch_adapter

if __name__ == "__main__":
    v2_consumer.set_dispatcher(_claude_dispatch_adapter)
    # Run watch with our interval
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--interval", type=float, default=3.0)
    p.add_argument("--max-ticks", type=int, default=None)
    p.add_argument("--recipients", default=None)
    args = p.parse_args()
    recipients = [r.strip() for r in args.recipients.split(",")] if args.recipients else None
    print(f"[start_consumer_real] dispatcher = {_claude_dispatch_adapter.__name__}", flush=True)
    print(f"[start_consumer_real] interval={args.interval}s max_ticks={args.max_ticks}", flush=True)
    v2_consumer.watch(recipients=recipients, interval_s=args.interval, max_ticks=args.max_ticks)