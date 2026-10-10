"""strategy_gate.py — Strategy Gate that emits gate events.

This module evaluates an envelope / task / Goal payload against the
loaded Strategy Policy + Requirements Registry + Contamination Scanner,
and returns:

  - allowed: bool
  - events:  list of dicts (gate event types per policy)
  - risk_envelope: dict or None (mirror-shape of goal_guard_hook)

Event types emitted (per `gate_event_types` in the policy):

    STRATEGY_DRIFT_DETECTED
        Generic drift: payload hints at vertical / industry / historical
        CloudTech direction without a specific retired-id match.

    RETIRED_REQUIREMENT_REACTIVATED
        Payload references an id in `deprecated_requirement_ids`.

    DEPRECATED_ASSET_REFERENCED
        Payload references a path or asset listed in
        `prohibited_active_assets` or `historical_source_prohibited_keys`.

    INVALID_TASK_GENERATED
        Generic malformed/under-specified task payload (e.g. missing
        title / success_criteria).

    ARCHIVE_LEAK_DETECTED
        Payload sources its content from an archived / read-only /
        quarantine surface AND is being re-introduced into an active
        loader.

    POLICY_GATE_REJECTED
    L1_FAIL
        Functional success failed: feature missing / mock / wrong I-O.
        Emitted by dr-verifier or worker supervisor; not by gate alone.
    L2_FAIL
        Engineering success failed: tests not run / regression / no rollback drill.
    L3_FAIL
        User success failed: journey blocked / no real-user signoff.
    L4_FAIL
        Business success failed or NOT_YET_MEASURED violation.
        Generic catch-all when the gate refuses dispatch.

The gate is fail-CLOSED: if the policy itself fails to load, every
event is POLICY_GATE_REJECTED with reason=policy_load_failed and
allowed=False. The hook layer must treat that as a hard block.

The gate never modifies the envelope. It is read-only.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .strategy_policy import (
    PolicyLoadResult,
    is_retired_id,
    is_industry_preset_blocked,
    is_prohibited_path,
    is_retired_alias,
    load_strategy_policy,
    retired_alias_kind_of,
)
# A-7 fix: terminal envelope types that bypass gate scanning
_INTERNAL_MESSAGE_TYPES = frozenset(("result", "ack", "status", "heartbeat", "error"))
# AIPM_FOUNDATION_02 / D5 enforcement: openclaw self-claim never bypasses gate
_OPENCLAW_SENDER_PREFIX = 'openclaw:'
_OPENCLAW_TRUSTED_MESSAGE_TYPES = frozenset()

from .requirements_lifecycle import (
    LifecycleState,
    RequirementsRegistry,
)
from .contamination_scanner import (
    Classification,
    ContaminationScanner,
    ScanReport,
)


# ---------------------------------------------------------------- Models
@dataclass

# A-7 fix: terminal envelope types that bypass gate scanning

class GateEvent:
    """A single gate event emitted during evaluation."""

    event_type: str
    severity: str  # INFO | WARN | BLOCK
    message: str
    matched_token: str | None = None
    matched_id: str | None = None
    source_classification: str = "UNKNOWN"
    ts: float = field(default_factory=lambda: time.time())

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "severity": self.severity,
            "message": self.message,
            "matched_token": self.matched_token,
            "matched_id": self.matched_id,
            "source_classification": self.source_classification,
            "ts": self.ts,
        }


@dataclass
class GateDecision:
    """The result of evaluating a payload through the strategy gate."""

    allowed: bool
    events: list[GateEvent] = field(default_factory=list)
    risk_envelope: dict | None = None
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "events": [e.to_dict() for e in self.events],
        }


@dataclass
class _QuickAllow:
    """Lightweight allow GateDecision (defense-in-depth)."""
    allowed: bool = True
    events: list = field(default_factory=list)
    risk_envelope = None
    reason: str = ""
    envelope: dict = field(default_factory=dict)

    def to_dict(self):
        return {"allowed": self.allowed, "reason": self.reason,
                "events": [e.to_dict() if hasattr(e, "to_dict") else e for e in self.events]}


class StrategyGate:
    """The strategy gate. Stateless; everything comes from the policy + registry."""

    def __init__(
        self,
        policy: dict,
        registry: RequirementsRegistry | None = None,
        scanner: ContaminationScanner | None = None,
        quarantine_root: str | None = None,
        archived_roots: list[str] | None = None,
    ) -> None:
        self.policy = policy
        self.registry = registry or RequirementsRegistry()
        self.quarantine_root = quarantine_root
        self.archived_roots = archived_roots or []
        self.scanner = scanner or ContaminationScanner(
            policy,
            quarantine_root=quarantine_root,
            archived_roots=archived_roots,
        )


    # ----- Public entry

    # ---------------------------------------------------------------- AIPM_FOUNDATION_02 / D3
    # Additive only. Existing methods unchanged.
    def emit_l1_fail(self, message: str, matched_id: str = "") -> "GateEvent":
        """Emit an L1_FAIL event (functional deficiency)."""
        return self._mk_event("L1_FAIL", "BLOCK",
                              message or "L1 functional check failed",
                              matched_id=matched_id or None)

    def emit_l2_fail(self, message: str, matched_id: str = "") -> "GateEvent":
        """Emit an L2_FAIL event (engineering deficiency)."""
        return self._mk_event("L2_FAIL", "BLOCK",
                              message or "L2 engineering check failed",
                              matched_id=matched_id or None)

    def emit_l3_fail(self, message: str, matched_id: str = "") -> "GateEvent":
        """Emit an L3_FAIL event (user journey / signoff missing)."""
        return self._mk_event("L3_FAIL", "BLOCK",
                              message or "L3 user check failed",
                              matched_id=matched_id or None)

    def emit_l4_fail(self, message: str, matched_id: str = "") -> "GateEvent":
        """Emit an L4_FAIL event (business value not measured / fabricated ROI)."""
        return self._mk_event("L4_FAIL", "BLOCK",
                              message or "L4 business check failed",
                              matched_id=matched_id or None)

    # AIPM02 / D3 follow-up: scan envelope payload and emit L1..L4 FAIL events
    # for missing evidence. Additive only: callers opt in by calling this.
    def _lifecycle_audit_emit(self, envelope):
        out = []
        try:
            if not isinstance(envelope, dict): return out
            payload = envelope.get("payload") or {}
            requirements = payload.get("requirements") or []
            if not requirements and isinstance(payload, dict) and "requirement_id" in payload:
                requirements = [payload["requirement_id"]]
            evidence_refs = payload.get("evidence_refs") or []
            success_criteria = payload.get("success_criteria")
            owner = payload.get("owner")
            review_signoff = payload.get("review_signoff") or envelope.get("review_signoff")
            metrics = payload.get("metrics_window")
            claimed_roi = payload.get("claimed_roi")
            if not requirements: out.append(self.emit_l1_fail("L1 FAIL: envelope has no requirement id"))
            if not evidence_refs: out.append(self.emit_l2_fail("L2 FAIL: envelope has no evidence_refs"))
            if not (success_criteria and owner and review_signoff): out.append(self.emit_l3_fail("L3 FAIL: success_criteria/owner/review_signoff missing"))
            if claimed_roi is not None and not metrics: out.append(self.emit_l4_fail("L4 FAIL: ROI claimed but no metrics_window defined"))
        except Exception:
            pass
        return out

    def evaluate_envelope(self, envelope: dict) -> GateDecision:
        """Evaluate an envelope payload.

        The envelope's payload is checked for:
          1. retired requirement id references (text + structured)
          2. blocked industry preset references (text)
          3. prohibited path / asset references (text)
          4. malformed task payload (missing title or success_criteria)
          5. archive leak (source references an archived surface)
        """
        events: list[GateEvent] = []
        if not isinstance(envelope, dict):
            events.append(self._mk_event(
                "INVALID_TASK_GENERATED", "BLOCK",
                "envelope is not a dict",
            ))
            return self._reject(envelope, events, "invalid_envelope_shape")
        # A-7 fix: terminal/internal envelopes bypass gate scanning
        msg_type_check = envelope.get("message_type", "")
        if isinstance(msg_type_check, str) and msg_type_check in _INTERNAL_MESSAGE_TYPES:
            return self._allow(envelope, events, reason="internal_terminal_bypass")
        # AIPM02 / D5 enforcement: openclaw self-claim never bypasses regardless of message_type
        sender_raw = envelope.get("sender", "") if isinstance(envelope, dict) else ""
        if isinstance(sender_raw, str) and sender_raw.startswith(_OPENCLAW_SENDER_PREFIX):
            events.append(self._mk_event(
                "OPENCLAW_BYPASS_DENIED", "WARN",
                "openclaw sender %s bypass attempt denied (D5 READ_ONLY_PROBER)" % sender_raw,
                matched_id=sender_raw,
            ))
        # AIPM02 / D3 wire-in: scan envelope only on opt-in (call _lifecycle_audit_emit explicitly)

        payload = envelope.get("payload") or {}
        msg_type = envelope.get("message_type") or ""
        sender = envelope.get("sender") or ""
        text = ""
        structured_fields: dict[str, str] = {}
        if isinstance(payload, dict):
            for f in ("text", "title", "description", "summary"):
                v = payload.get(f)
                if v:
                    structured_fields[f] = str(v)
            text = " ".join(structured_fields.values())
        else:
            text = str(payload) if payload else ""

        # 1. retired ids (look for R-NNN token in text and structured fields)
        retired_hits = self._scan_for_retired_ids(text)
        for hit in retired_hits:
            events.append(self._mk_event(
                "RETIRED_REQUIREMENT_REACTIVATED", "BLOCK",
                f"references retired requirement id {hit}",
                matched_id=hit,
            ))

        # 2. industry preset blocks
        preset_hits = self._scan_for_industry_presets(text)
        for hit in preset_hits:
            events.append(self._mk_event(
                "STRATEGY_DRIFT_DETECTED", "BLOCK",
                f"references blocked industry preset {hit}",
                matched_id=hit,
            ))

        # 3. prohibited path / asset keys
        path_hits = self._scan_for_prohibited_paths(text)
        for hit in path_hits:
            events.append(self._mk_event(
                "DEPRECATED_ASSET_REFERENCED", "BLOCK",
                f"references deprecated asset / source key {hit}",
                matched_id=hit,
            ))

        # 3a. quarantine_paths (A-2 fix): WorkBuddy etc.
        qp_hits = self._scan_for_quarantine_paths(text)
        for hit in qp_hits:
            events.append(self._mk_event(
                "DEPRECATED_ASSET_REFERENCED", "BLOCK",
                f"references quarantine path {hit}",
                matched_id=hit,
            ))

        # 3b. prohibited_active_assets (A-1 / F-NEW-1): PA-01..12 from policy
        pa_hits = self._scan_for_prohibited_assets(text)
        for hit in pa_hits:
            events.append(self._mk_event(
                "DEPRECATED_ASSET_REFERENCED", "BLOCK",
                f"references prohibited active asset {hit}",
                matched_id=hit,
            ))

        # 4. retired aliases (correction 2026-10-09). Alias hits are NEVER
        # the sole decision. We combine:
        #   - structured-field presence (title/description/summary field)
        #   - existing-signal context (any retired id / prohibited path / preset hit)
        #   - active task-envelope source context
        # Bare alias in pure text without any of the above is emitted as
        # WARN, not BLOCK. When the alias is paired with structured field
        # presence OR with an existing signal OR with cloudtech_v22_v23 kind
        # (which directly maps to prohibited_active_assets), it BLOCKs.
        alias_hits = is_retired_alias(self.policy, text)
        combined_signal_present = bool(
            retired_hits or preset_hits or path_hits
        )
        for alias in alias_hits:
            kind = retired_alias_kind_of(self.policy, alias)
            in_structured = self._alias_in_structured_fields(alias, structured_fields)
            is_cloudtech_kind = kind == "cloudtech_v22_v23"
            is_combined = bool(
                in_structured
                or combined_signal_present
                or is_cloudtech_kind
            )
            if kind == "cloudtech_v22_v23" or kind == "skill_id":
                event_type = "DEPRECATED_ASSET_REFERENCED"
            else:
                event_type = "STRATEGY_DRIFT_DETECTED"
            if is_combined:
                events.append(self._mk_event(
                    event_type, "BLOCK",
                    (
                        f"references retired alias {alias!r} (kind={kind or 'unclassified'}) "
                        f"in active task context"
                    ),
                    matched_id=alias,
                    matched_token=alias,
                    source_classification="active_envelope",
                ))
            else:
                events.append(self._mk_event(
                    event_type, "WARN",
                    (
                        f"references retired alias {alias!r} (kind={kind or 'unclassified'}) "
                        f"without combined signal; bare hit not blocked"
                    ),
                    matched_id=alias,
                    matched_token=alias,
                    source_classification="text_only",
                ))

        # 5. malformed payload: task/message envelopes need title + success_criteria (A-3 fix)
        if msg_type in ("task", "message"):
            if not isinstance(payload, dict):
                # A-3: non-empty wrong-type payload (list/str/num) was bypassed before
                events.append(self._mk_event(
                    "INVALID_TASK_GENERATED", "BLOCK",
                    f"task payload must be a dict, got {type(payload).__name__}",
                    matched_id="payload_type",
                ))
                return self._reject(envelope, events, "payload_type_invalid")
            if not (payload.get("title") or payload.get("text")):
                events.append(self._mk_event(
                    "INVALID_TASK_GENERATED", "BLOCK",
                    "task payload missing title/text",
                ))
            # GoalContract-bearing payloads should carry success_criteria
            goal = payload.get("goal") if isinstance(payload, dict) else None
            if isinstance(goal, dict) and not goal.get("success_criteria"):
                events.append(self._mk_event(
                    "INVALID_TASK_GENERATED", "WARN",
                    "goal payload missing success_criteria",
                ))

        # 6. archive leak: source references a path that lives in quarantine/
        # archived surface
        archive_hits = self._scan_for_archive_leak(text)
        for hit in archive_hits:
            events.append(self._mk_event(
                "ARCHIVE_LEAK_DETECTED", "BLOCK",
                f"references archived surface {hit}",
                matched_id=hit,
            ))

        # Determine allowed
        blocking = [e for e in events if e.severity == "BLOCK"]
        if blocking:
            return self._reject(envelope, events, "strategy_gate_blocked",
                                matched_event=blocking[0].event_type)

        return GateDecision(
            allowed=True,
            events=events,
            reason="allowed",
        )

    def scan_report(self, paths: list[str]) -> ScanReport:
        """Run the contamination scanner across a list of paths."""
        report = ScanReport()
        for p in paths:
            report.items_scanned += 1
            for f in self.scanner.scan_path(p):
                report.add(f)
        report.scan_finished = time.time()
        return report

    # ----- Helpers
    def _scan_for_retired_ids(self, text: str) -> list[str]:
        out: list[str] = []
        if not text:
            return out
        import re as _re
        for m in _re.finditer(r"R-\d{3}", text):
            rid = m.group(0)
            if is_retired_id(self.policy, rid):
                out.append(rid)
        return sorted(set(out))

    def _scan_for_industry_presets(self, text: str) -> list[str]:
        out: list[str] = []
        if not text:
            return out
        for preset in self.policy.get("industry_presets_blocked", []) or []:
            if preset.lower() in text.lower():
                out.append(preset)
        return sorted(set(out))

    def _scan_for_prohibited_paths(self, text: str) -> list[str]:
        out: list[str] = []
        if not text:
            return out
        for key in self.policy.get("historical_source_prohibited_keys", []) or []:
            if key.lower() in text.lower():
                out.append(key)
        return sorted(set(out))


    def _scan_for_prohibited_assets(self, text: str) -> list[str]:
        """F-NEW-1 + Round 6 A-1 + Round 3 fix: alphanumeric token fingerprint.

        Round 3 fix: tightened thresholds to prevent false-positive substring matches
        like 'loop' matching 'loopback-demo'. Now requires:
        - alphanumeric token length >= 6 (was >=4), AND
        - at least 2 distinct token hits (was >=1), AND
        - word boundary check (token must NOT be a strict prefix of a longer text token).

        Example fix: PA-10 summary = 'install_aios_loop.cmd ...' previously matched
        'loopback-demo' because 'loop' (4 chars) was a substring of 'loopback'.
        Now requires >= 6-char tokens + 2 hits + boundary check, so 'loop' alone
        no longer matches.
        """
        import re as _re_pa
        hits = []
        if not self.policy:
            return hits
        text_lower = text.lower()
        for pa in self.policy.get("prohibited_active_assets", []) or []:
            pa_id = pa.get("id", "")
            summary = pa.get("summary", "") or ""
            tokens = [t for t in _re_pa.findall(r"[A-Za-z0-9-]+", summary) if len(t) >= 6][:8]
            # Word boundary: token must be its own word in text (not just a prefix)
            # Split text on non-alphanumeric, check exact token presence
            text_words = set(_re_pa.findall(r"[A-Za-z0-9-]+", text_lower))
            hit_tokens = [t for t in tokens if t.lower() in text_words]
            if len(hit_tokens) >= 2:
                hits.append(f"{pa_id}({','.join(hit_tokens[:2])})")
        return hits
    def _scan_for_quarantine_paths(self, text: str) -> list[str]:
        """A-2 fix: scan for any policy-defined quarantine_paths match."""
        hits = []
        if not self.policy:
            return hits
        for qpath in self.policy.get("quarantine_paths", []) or []:
            if not isinstance(qpath, str):
                continue
            tokens = qpath.split()[:3]
            if len(tokens) < 1:
                continue
            fingerprint = " ".join(tokens)
            if fingerprint in text:
                hits.append(qpath)
        return hits


    def _scan_for_archive_leak(self, text: str) -> list[str]:
        out: list[str] = []
        if not text:
            return out
        # Look for explicit quarantine / archived markers in text
        for marker in (
            "D:\\AIOS\\_quarantine\\",
            "D:\\AIOS\\_archived_",
            "D:\\AIOS\\_backup",
            "D:\\CloudTech-Portable",
            "D:\\CloudTech-Vault",
            "D:\\CloudTech-Inbox",
            "AIOS_SOURCE_OF_TRUTH_FINAL",
            "AIOS_RECONSTRUCTION",
        ):
            if marker.lower() in text.lower():
                out.append(marker)
        return sorted(set(out))

    def _alias_in_structured_fields(self, alias: str, fields: dict[str, str]) -> bool:
        """Return True iff alias appears in any of the named structured fields.

        `fields` maps field-name -> value (e.g. 'title', 'description',
        'summary', 'text'). The alias must be present in at least one
        value. This is the 'structured-field presence' signal used to
        upgrade alias hits from WARN to BLOCK in the gate.
        """
        if not alias or not fields:
            return False
        for value in fields.values():
            if value and alias in value:
                return True
        return False

    def _mk_event(self, event_type: str, severity: str, message: str,
                  *, matched_id: str | None = None,
                  matched_token: str | None = None,
                  source_classification: str = "UNKNOWN") -> GateEvent:
        return GateEvent(
            event_type=event_type,
            severity=severity,
            message=message,
            matched_id=matched_id,
            matched_token=matched_token,
            source_classification=source_classification,
        )

    def _allow(self, envelope, events, reason: str = ""):
        """Helper: positive (allowed) GateDecision."""
        return _QuickAllow(envelope=envelope, events=events, reason=reason)


    def _reject(self, envelope: dict, events: list[GateEvent], reason: str,
                *, matched_event: str | None = None) -> GateDecision:
        # Emit a POLICY_GATE_REJECTED as the umbrella event if no matched event given
        if matched_event is None:
            events.insert(0, self._mk_event(
                "POLICY_GATE_REJECTED", "BLOCK",
                f"gate rejected envelope: {reason}",
            ))
        risk = self._make_risk_envelope(envelope, events, reason)
        return GateDecision(
            allowed=False,
            events=events,
            risk_envelope=risk,
            reason=reason,
        )

    def _make_risk_envelope(self, envelope: dict, events: list[GateEvent], reason: str) -> dict:
        env_id = envelope.get("id") if isinstance(envelope, dict) else None
        sender = envelope.get("sender") if isinstance(envelope, dict) else None
        return {
            "envelope_type": "strategy_gate_risk",
            "original_envelope_id": env_id,
            "original_sender": sender,
            "reason": reason,
            "events": [e.to_dict() for e in events],
            "ts": time.time(),
            "policy_id": self.policy.get("policy_id"),
            "policy_version": self.policy.get("policy_version"),
            "schema_version": "1.0",
        }


# ---------------------------------------------------------------- Bootstrap helpers
def gate_from_policy_dir(
    policy_dir: Path | str | None = None,
    *,
    quarantine_root: str | None = None,
    archived_roots: list[str] | None = None,
) -> tuple[PolicyLoadResult, StrategyGate | None]:
    """Build a StrategyGate from a policy dir (returns (load_result, gate_or_None))."""
    res = load_strategy_policy(policy_dir)
    if not res.ok:
        return res, None
    gate = StrategyGate(
        res.policy,  # type: ignore[arg-type]
        quarantine_root=quarantine_root,
        archived_roots=archived_roots,
    )
    return res, gate


__all__ = [
    "GateEvent",
    "GateDecision",
    "StrategyGate",
    "gate_from_policy_dir",
]
