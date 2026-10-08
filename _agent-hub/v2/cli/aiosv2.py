# v2/cli/aiosv2.py — single CLI entry for AIOS Hub v2.
#
# Usage:
#   python aiosv2.py init
#   python aiosv2.py status
#   python aiosv2.py health
#   python aiosv2.py send --from codex --to claudecode --type message --payload '{"text":"hi"}'
#     [--correlation-id <env_id>] [--in-reply-to <env_id>] [--dest {inbox,outbox}]
#   python aiosv2.py receive [--limit N] [--claim] [--agent codex]
#   python aiosv2.py ack <envelope_id> --actor claudecode [--note ...] [--dest {inbox,outbox}]
#   python aiosv2.py submit-task --title "..." --assignee codex --owner claudecode [--timeout-ms 60000]
#   python aiosv2.py update-task --task-id <uuid> --state running|--actor claudecode
#   python aiosv2.py watch [--interval 5]
#
# R320.6 ack routing: `ack` writes the ack envelope to inbox by default
# (recipient=original.sender), so the original sender can receive the ack
# via `receive --agent <sender>`. There is NO outbox → inbox dispatcher;
# `--dest outbox` is kept only as an explicit audit-only override.
#
# Exit codes: 0 OK / 1 usage / 2 not found / 3 validation failed / 4 dedup
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

# Make `src` importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.envelope import (build_envelope, envelope_from_json, envelope_to_json,
                           envelope_to_chunks,
                           reply_envelope, verify_envelope)
from src.id import new_uuid, utc_now_iso
from src.paths import (DEADLETTER, INBOX, OUTBOX, REPORTS_DIR, STATE_FILE, V2_ROOT,
                        ensure_dirs)
from src.probes import probe_all
from src.queue import ack as q_ack, claim as q_claim, deadletter, enqueue, get_envelope_by_id, list_unclaimed
from src.state_machine import (build_state_snapshot, cancel, get_task, heartbeat,
                                list_tasks, save_state_snapshot, submit_task,
                                transition)
from src.supervisor import tick as sup_tick, watch as sup_watch
from src.validation import validate_task


def cmd_init(_: argparse.Namespace) -> int:
    ensure_dirs()
    snap = save_state_snapshot(build_state_snapshot())
    (REPORTS_DIR / "INIT_OK.txt").write_text(
        f"initialized at {utc_now_iso()}\nv2_root={V2_ROOT}\nstate={snap}\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "v2_root": str(V2_ROOT), "state": str(snap)},
                     ensure_ascii=False, indent=2))
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    ensure_dirs()
    tasks = list_tasks()

    def _count_settling_json_files(d):
        """Count committed envelopes in `d` (excludes tmp/claimed/dead sidecars).
        R320.3 fix: glob returns a generator; len() on a generator raises TypeError.
        Wrap in list() AND filter sidecars."""
        return sum(1 for p in d.glob("*.json")
                   if ".tmp." not in p.name
                   and ".claimed." not in p.name
                   and ".dead." not in p.name)

    inbox_count = _count_settling_json_files(INBOX)
    outbox_count = _count_settling_json_files(OUTBOX)
    dead_count = _count_settling_json_files(DEADLETTER)

    # R320.4: status must be resilient. If the agent registry is missing or
    # corrupt, do NOT crash — return agents_in_registry=0 + warnings list.
    warnings = []
    registry_path = V2_ROOT / "agents" / "agents.json"
    agents_in_registry = 0
    if not registry_path.exists():
        warnings.append(f"agents registry missing: {registry_path} "
                        "(run `aiosv2.py init` to create from template)")
    else:
        try:
            data = json.loads(registry_path.read_text(encoding="utf-8"))
            agents_in_registry = len(data.get("agents", []))
        except (json.JSONDecodeError, KeyError, OSError, UnicodeDecodeError) as e:
            warnings.append(f"agents registry unreadable: {registry_path} "
                            f"({type(e).__name__}: {e}); agents_in_registry=0")

    print(json.dumps({
        "ts": utc_now_iso(),
        "v2_root": str(V2_ROOT),
        "tasks_total": len(tasks),
        "tasks_by_state": _counter(tasks),
        "inbox_count": inbox_count,
        "outbox_count": outbox_count,
        "deadletter_count": dead_count,
        "agents_in_registry": agents_in_registry,
        "registry_path": str(registry_path),
        "registry_exists": registry_path.exists(),
        "warnings": warnings,
        "state_file_exists": STATE_FILE.exists(),
    }, ensure_ascii=False, indent=2))
    return 0


def _counter(tasks):
    c = {}
    for t in tasks:
        c[t["state"]] = c.get(t["state"], 0) + 1
    return c


def cmd_health(_: argparse.Namespace) -> int:
    print(json.dumps(probe_all(), ensure_ascii=False, indent=2))
    return 0


def cmd_send(args: argparse.Namespace) -> int:
    payload = json.loads(args.payload) if args.payload else {}
    env = build_envelope(
        sender=args.fr,
        recipient=args.to,
        message_type=args.type,
        payload=payload,
        artifact_refs=json.loads(args.artifact_refs) if args.artifact_refs else None,
        ttl_ms=args.ttl_ms,
        correlation_id=args.correlation_id,
        in_reply_to=args.in_reply_to,
    )
    # R286: if --chunk-size N is set and payload.text exceeds N bytes,
    # split the envelope into N-byte chunks.  Default = single envelope.
    chunk_size = getattr(args, "chunk_size", None)
    if chunk_size and isinstance(payload, dict) and isinstance(payload.get("text"), str):
        chunks = envelope_to_chunks(env, max_chunk_size=chunk_size)
        if chunks:
            chunk_results = []
            for c in chunks:
                cr = enqueue(c, dest=args.dest)
                chunk_results.append({"id": c["id"], "deduped": cr["deduped"],
                                       "file": cr.get("file")})
            print(json.dumps({
                "ok": True, "chunked": True, "envelope_id": env["id"],
                "parent_envelope_id": env["id"],
                "chunk_size": chunk_size,
                "chunk_count": len(chunks),
                "chunks": chunk_results,
                "dest": args.dest,
            }, ensure_ascii=False, indent=2))
            return 0
    res = enqueue(env, dest=args.dest)
    print(json.dumps({"ok": True, "deduped": res["deduped"], "envelope_id": env["id"],
                       "correlation_id": env.get("correlation_id"),
                       "in_reply_to": env.get("in_reply_to"),
                       "dest": args.dest},
                      ensure_ascii=False, indent=2))
    return 0


def cmd_receive(args: argparse.Namespace) -> int:
    # R320.3: --agent filters by recipient BEFORE the limit is applied,
    # so an agent can find its own messages even when the queue is full.
    items = list_unclaimed(INBOX, limit=args.limit, recipient=args.agent)
    out = []
    for path, env in items:
        rec = {"envelope_id": env["id"], "message_type": env["message_type"],
               "sender": env["sender"], "recipient": env["recipient"],
               "timestamp": env["timestamp"], "file": str(path.name)}
        if args.claim:
            claimed = q_claim(path)
            if claimed:
                rec["claimed"] = str(claimed.name)
            else:
                rec["claimed"] = None
        out.append(rec)
    print(json.dumps({"count": len(out), "items": out,
                       "filter": {"agent": args.agent}}, ensure_ascii=False, indent=2))
    return 0


def cmd_ack(args: argparse.Namespace) -> int:
    """Ack a previously-claimed envelope by id.

    R320.3 fix: do NOT call get_envelope_by_id() here — that helper
    explicitly excludes `.claimed.*` files (because they are claimed,
    not unclaimed), so it always returns None after a claim.

    Instead: glob inbox for <envelope_id>__*.claimed.*.json directly,
    parse the claimed file to recover the envelope dict, then q_ack.

    R320.6 fix: emit the ack envelope to INBOX by default (recipient =
    original.sender), so the original sender can `receive --agent <sender>`
    and claim it. There is NO dispatcher that copies outbox → inbox, so
    writing the ack to outbox previously made it un-deliverable. Outbox
    is now reserved as an explicit audit-only destination via
    `--dest outbox`. Default `inbox` ensures real two-process round-trip.
    """
    eid = args.envelope_id
    claimed_files = list(INBOX.glob(f"{eid}__*.claimed.*.json"))
    if not claimed_files:
        print(json.dumps({"ok": False, "error": f"no claimed file for envelope_id={eid} "
                                                  "(must run `receive --claim` first)"},
                          ensure_ascii=False))
        return 2
    claimed_path = claimed_files[0]
    try:
        env = envelope_from_json(claimed_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"failed to parse claimed file: {e}"},
                          ensure_ascii=False))
        return 2
    if q_ack(claimed_path):
        # R320.6: build ack envelope via reply_envelope so correlation_id +
        # in_reply_to are wired to original.id automatically.
        # Default dest="inbox" so the original sender can receive the ack
        # via `receive --agent <sender>`. Use --dest outbox for audit-only.
        ack_env = reply_envelope(env, sender=args.actor, message_type="ack",
                                  payload={"ack_of": env["id"], "note": args.note or ""})
        res = enqueue(ack_env, dest=args.dest)
        print(json.dumps({
            "ok": True,
            "acked_envelope_id": env["id"],
            "ack_envelope_id": ack_env["id"],
            "note": args.note or "",
            "ack_recipient": ack_env["recipient"],
            "ack_correlation_id": ack_env.get("correlation_id"),
            "ack_in_reply_to": ack_env.get("in_reply_to"),
            "ack_dest": args.dest,
            "deduped": res["deduped"],
        }, ensure_ascii=False))
        return 0
    print(json.dumps({"ok": False, "error": "q_ack returned False"}, ensure_ascii=False))
    return 2


def cmd_submit_task(args: argparse.Namespace) -> int:
    inp = json.loads(args.input_payload) if args.input_payload else {}
    task = submit_task(
        title=args.title, assignee=args.assignee, owner=args.owner,
        description=args.description or "", timeout_ms=args.timeout_ms,
        max_retries=args.max_retries, input_payload=inp,
    )
    print(json.dumps({"ok": True, "task_id": task["task_id"], "state": task["state"]},
                     ensure_ascii=False, indent=2))
    return 0


def cmd_update_task(args: argparse.Namespace) -> int:
    if args.action == "transition":
        op = json.loads(args.output_payload) if args.output_payload else None
        err = json.loads(args.error) if args.error else None
        t = transition(args.task_id, args.state, actor=args.actor,
                        output_payload=op, error=err, note=args.note or "")
        print(json.dumps({"ok": True, "task_id": t["task_id"], "state": t["state"]},
                         ensure_ascii=False, indent=2))
    elif args.action == "heartbeat":
        t = heartbeat(args.task_id, actor=args.actor)
        print(json.dumps({"ok": True, "task_id": t["task_id"], "heartbeat_at": t["heartbeat_at"]},
                         ensure_ascii=False, indent=2))
    elif args.action == "cancel":
        t = cancel(args.task_id, actor=args.actor)
        print(json.dumps({"ok": True, "task_id": t["task_id"], "state": t["state"]},
                         ensure_ascii=False, indent=2))
    else:
        print(json.dumps({"ok": False, "error": f"unknown action {args.action!r}"}, ensure_ascii=False))
        return 1
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    sup_watch(interval_s=args.interval, max_ticks=args.max_ticks)
    return 0


def cmd_tick(_: argparse.Namespace) -> int:
    print(json.dumps(sup_tick(), ensure_ascii=False, indent=2, default=str))
    return 0


def main():
    p = argparse.ArgumentParser(prog="aiosv2")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init").set_defaults(func=cmd_init)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("health").set_defaults(func=cmd_health)
    sub.add_parser("tick").set_defaults(func=cmd_tick)

    s_send = sub.add_parser("send")
    s_send.add_argument("--from", dest="fr", required=True)
    s_send.add_argument("--to", required=True)
    s_send.add_argument("--type", required=True,
                        choices=["message", "task", "status", "result", "ack",
                                  "heartbeat", "error"])
    s_send.add_argument("--payload", default="{}")
    s_send.add_argument("--artifact-refs", default=None)
    s_send.add_argument("--ttl-ms", type=int, default=300000)
    # R320.6: optional correlation metadata so CLI send can mark result/status/
    # error envelopes as replies. Both optional; omission preserves R320/R320.1
    # compatibility.
    s_send.add_argument("--correlation-id", default=None,
                        help="envelope.correlation_id (e.g. original envelope id "
                              "for a reply). Optional; omitted => envelope has no "
                              "correlation_id field.")
    s_send.add_argument("--in-reply-to", default=None,
                        help="envelope.in_reply_to (e.g. original envelope id for "
                              "a reply). Optional; omitted => envelope has no "
                              "in_reply_to field.")
    s_send.add_argument("--dest", choices=["inbox", "outbox"], default="inbox")
    # R286: chunked large-text support (default 32 KiB per chunk).
    # When payload.text exceeds this size, cmd_send splits into N chunk envelopes
    # (each carries payload.text_chunks[] + parent_envelope_id via correlation_id).
    s_send.add_argument("--chunk-size", type=int, default=None,
                        help="R286: split payload.text into chunks of N bytes "
                             "(default 32768 = 32 KiB). Omit to send single envelope.")
    s_send.set_defaults(func=cmd_send)

    s_recv = sub.add_parser("receive")
    s_recv.add_argument("--limit", type=int, default=50)
    s_recv.add_argument("--claim", action="store_true")
    s_recv.add_argument("--agent", default=None,
                         help="filter by recipient agent_id (applied BEFORE --limit). "
                              "Use 'any' or omit to receive all unclaimed.")
    s_recv.set_defaults(func=cmd_receive)

    s_ack = sub.add_parser("ack")
    s_ack.add_argument("envelope_id")
    s_ack.add_argument("--actor", required=True)
    s_ack.add_argument("--note", default="")
    # R320.6: default to inbox so ack is deliverable to original.sender.
    # `--dest outbox` is kept as an explicit audit-only override.
    s_ack.add_argument("--dest", choices=["inbox", "outbox"], default="inbox",
                        help="where to write the ack envelope. Default 'inbox' "
                              "(recipient=original.sender) so the sender can "
                              "receive the ack. Use 'outbox' ONLY for audit "
                              "purposes — outbox has no dispatcher.")
    s_ack.set_defaults(func=cmd_ack)

    s_st = sub.add_parser("submit-task")
    s_st.add_argument("--title", required=True)
    s_st.add_argument("--assignee", required=True)
    s_st.add_argument("--owner", required=True)
    s_st.add_argument("--description", default="")
    s_st.add_argument("--timeout-ms", type=int, default=60000)
    s_st.add_argument("--max-retries", type=int, default=3)
    s_st.add_argument("--input-payload", default=None)
    s_st.set_defaults(func=cmd_submit_task)

    s_ut = sub.add_parser("update-task")
    s_ut.add_argument("--task-id", required=True)
    s_ut.add_argument("--action", required=True,
                       choices=["transition", "heartbeat", "cancel"])
    s_ut.add_argument("--state", choices=["queued", "running", "waiting",
                                            "succeeded", "failed", "cancelled"])
    s_ut.add_argument("--actor", required=True)
    s_ut.add_argument("--note", default="")
    s_ut.add_argument("--output-payload", default=None)
    s_ut.add_argument("--error", default=None)
    s_ut.set_defaults(func=cmd_update_task)

    s_w = sub.add_parser("watch")
    s_w.add_argument("--interval", type=float, default=5.0)
    s_w.add_argument("--max-ticks", type=int, default=None)
    s_w.set_defaults(func=cmd_watch)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())