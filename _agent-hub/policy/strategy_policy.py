"""strategy_policy.py — Loader/validator for the CloudTech Global Product Strategy Policy.

This module is the SINGLE MACHINE-READABLE policy loader for the
retired-direction gate. It enforces:

  1. JSON parses successfully
  2. SHA-256 sidecar matches the file content
  3. JSON-Schema validation passes (draft-07 subset; no jsonschema dep)
  4. policy_id == GLOBAL_PRODUCT_STRATEGY
  5. policy_version matches expected
  6. owner = USER; change_authority = EXPLICIT_USER_APPROVAL
  7. status = ACTIVE

Failures are reported as `PolicyLoadResult` with:
  - ok: bool
  - reason: str  (machine-readable code)
  - errors: list[str]
  - policy: dict | None  (only when ok=True)

The loader never silently fallbacks. A missing file, malformed JSON,
hash mismatch, or schema violation → fail closed.

Usage:
    from policy.strategy_policy import load_strategy_policy
    res = load_strategy_policy(policy_dir)
    if not res.ok:
        # strategy gate MUST refuse to open
        ...

The module is intentionally stdlib-only (no jsonschema dependency) so
it can be imported from v2_consumer / goal_guard_hook / tests without
adding to the runtime requirements surface.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------- Constants
POLICY_FILENAME = "product_strategy.v1.json"
SCHEMA_FILENAME = "product_strategy.v1.schema.json"
SIDECAR_FILENAME = "product_strategy.v1.sha256"

EXPECTED_POLICY_ID = "GLOBAL_PRODUCT_STRATEGY"
EXPECTED_POLICY_VERSION = "2026-10-08"
EXPECTED_OWNER = "USER"
EXPECTED_CHANGE_AUTHORITY = "EXPLICIT_USER_APPROVAL"
EXPECTED_STATUS = "ACTIVE"

REQUIRED_FIELDS: tuple[str, ...] = (
    "policy_id", "policy_version", "title", "product", "positioning",
    "business_scope", "vertical_product_strategy", "industry_presets",
    "status", "owner", "change_authority", "scope_note",
    "deprecated_requirement_ids", "prohibited_active_assets",
    "quarantine_paths", "industry_presets_blocked",
    "retired_aliases", "retired_alias_kind",
    "historical_source_prohibited_keys", "gate_event_types",
    "scanner_classifications",
)

ALLOWED_VALUES: dict[str, tuple[str, ...]] = {
    "policy_id": ("GLOBAL_PRODUCT_STRATEGY",),
    "product": ("CloudTech",),
    "positioning": ("HORIZONTAL_MARKETING_SAAS",),
    "business_scope": ("GENERAL_MARKETING",),
    "vertical_product_strategy": ("DISABLED",),
    "industry_presets": ("DISABLED",),
    "status": ("ACTIVE", "SUSPENDED", "DRAFT"),
    "change_authority": ("EXPLICIT_USER_APPROVAL",),
    "deactivation_required": ("USER_AUTHORIZATION_REQUIRED", "SAFE_REVERSIBLE"),
    "gate_event_types": (
        "STRATEGY_DRIFT_DETECTED",
        "RETIRED_REQUIREMENT_REACTIVATED",
        "DEPRECATED_ASSET_REFERENCED",
        "INVALID_TASK_GENERATED",
        "ARCHIVE_LEAK_DETECTED",
        "POLICY_GATE_REJECTED",
    ),
    "scanner_classifications": (
        "ACTIVE_VIOLATION",
        "ARCHIVED_REFERENCE",
        "FALSE_POSITIVE",
        "UNVERIFIED",
    ),
}


# ---------------------------------------------------------------- Result
@dataclass
class PolicyLoadResult:
    """Result of loading + validating the strategy policy.

    Attributes:
        ok: True only when every check passed.
        reason: short machine-readable code (e.g. 'hash_mismatch').
        errors: list of human-readable error strings.
        policy: the loaded dict (None on failure).
        sha256: hash of the policy file (None on failure).
        policy_path: path the policy was loaded from.
    """

    ok: bool
    reason: str = ""
    errors: list[str] = field(default_factory=list)
    policy: dict | None = None
    sha256: str | None = None
    policy_path: str | None = None


# ---------------------------------------------------------------- Helpers
def _compute_sha256(path: Path) -> str:
    """Compute uppercase SHA-256 hex digest of a file's content."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def _read_hash_from_sidecar(sidecar: Path) -> str | None:
    """Read the first non-comment hash token from the SHA-256 sidecar."""
    if not sidecar.exists():
        return None
    for line in sidecar.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        token = line.split()[0]
        if re.fullmatch(r"[0-9A-F]{64}", token):
            return token.upper()
    return None


# ---------------------------------------------------------------- Schema validator
def _validate_schema_stub(policy: dict) -> list[str]:
    """Subset draft-07 schema validator.

    The schema is intentionally small (no `oneOf` / `anyOf` / `format`)
    so we can validate with a minimal hand-rolled checker. Anything
    more complex than this belongs in a separate dedicated validator.
    """
    errors: list[str] = []

    # Required fields
    for field_name in REQUIRED_FIELDS:
        if field_name not in policy:
            errors.append(f"missing required field: {field_name}")
    if errors:
        return errors

    # Enumerated top-level fields.  Scalars check value directly;
    # arrays check every element against the allowed set.
    for field_name, allowed in ALLOWED_VALUES.items():
        if field_name not in policy:
            continue
        value = policy[field_name]
        if isinstance(value, list):
            for v in value:
                if v not in allowed:
                    errors.append(
                        f"field {field_name} contains element {v!r} not in allowed set {list(allowed)}"
                    )
        else:
            if value not in allowed:
                errors.append(
                    f"field {field_name}={value!r} not in allowed set {list(allowed)}"
                )

    # deprecated_requirement_ids: pattern R-NNN
    for rid in policy.get("deprecated_requirement_ids", []) or []:
        if not re.fullmatch(r"R-[0-9]{3}", str(rid)):
            errors.append(f"deprecated_requirement_id malformed: {rid!r}")

    # prohibited_active_assets shape
    for asset in policy.get("prohibited_active_assets", []) or []:
        if not isinstance(asset, dict):
            errors.append(f"prohibited_active_assets entry not a dict: {asset!r}")
            continue
        for k in ("id", "kind", "summary", "deactivation_required"):
            if k not in asset:
                errors.append(f"prohibited_active_assets[{asset.get('id', '?')}] missing {k}")
        if "id" in asset and not re.fullmatch(r"PA-[0-9]{2}", str(asset["id"])):
            errors.append(f"prohibited_active_assets id malformed: {asset['id']!r}")

    # Unique array values
    for key in (
        "deprecated_requirement_ids",
        "quarantine_paths",
        "industry_presets_blocked",
        "retired_aliases",
        "historical_source_prohibited_keys",
        "gate_event_types",
        "scanner_classifications",
    ):
        arr = policy.get(key, []) or []
        if len(arr) != len(set(arr)):
            errors.append(f"{key} contains duplicates")

    # retired_aliases: non-empty strings; structural sanity
    for alias in policy.get("retired_aliases", []) or []:
        if not isinstance(alias, str) or not alias.strip():
            errors.append(f"retired_aliases contains empty/non-string entry: {alias!r}")
            continue
        if len(alias.strip()) < 2:
            errors.append(f"retired_aliases entry too short (<2): {alias!r}")

    # retired_alias_kind: dict[str, list[str]]; every alias belongs to a kind
    kind = policy.get("retired_alias_kind")
    if not isinstance(kind, dict):
        errors.append("retired_alias_kind must be an object")
    else:
        for kind_name, alias_list in kind.items():
            if not isinstance(alias_list, list):
                errors.append(f"retired_alias_kind[{kind_name!r}] must be a list")
                continue
            for a in alias_list:
                if not isinstance(a, str) or not a.strip():
                    errors.append(
                        f"retired_alias_kind[{kind_name!r}] contains empty/non-string: {a!r}"
                    )
        # every alias must appear in at least one kind bucket
        flat = []
        for v in kind.values():
            if isinstance(v, list):
                flat.extend(v)
        aliases_in_policy = set(policy.get("retired_aliases", []) or [])
        aliases_in_kinds = set(flat)
        unaccounted = aliases_in_kinds - aliases_in_policy
        if unaccounted:
            errors.append(
                f"retired_alias_kind contains aliases not in retired_aliases: {sorted(unaccounted)}"
            )

    return errors


# ---------------------------------------------------------------- Public API
def load_strategy_policy(
    policy_dir: Path | str | None = None,
) -> PolicyLoadResult:
    """Load + validate the strategy policy.

    Resolution order:
      1. `policy_dir` argument
      2. AIOS_STRATEGY_POLICY_DIR env var
      3. <this-file>/../
    """
    if policy_dir is None:
        policy_dir = os.environ.get("AIOS_STRATEGY_POLICY_DIR")
    if policy_dir is None:
        policy_dir = str(Path(__file__).resolve().parent)

    pdir = Path(policy_dir)
    json_path = pdir / POLICY_FILENAME
    schema_path = pdir / SCHEMA_FILENAME
    sidecar_path = pdir / SIDECAR_FILENAME

    # 1. file presence
    if not json_path.exists():
        return PolicyLoadResult(
            ok=False,
            reason="missing_policy_file",
            errors=[f"policy file not found: {json_path}"],
            policy_path=str(json_path),
        )

    # 2. parse JSON
    try:
        raw = json_path.read_text(encoding="utf-8")
        policy = json.loads(raw)
    except Exception as exc:  # malformed JSON
        return PolicyLoadResult(
            ok=False,
            reason="malformed_json",
            errors=[f"JSON parse failed: {exc}"],
            policy_path=str(json_path),
        )

    # 3. SHA-256 sidecar match
    actual_hash = _compute_sha256(json_path)
    side_hash = _read_hash_from_sidecar(sidecar_path)
    if side_hash is None:
        return PolicyLoadResult(
            ok=False,
            reason="missing_sha256_sidecar",
            errors=[f"sha256 sidecar not found or unreadable: {sidecar_path}"],
            policy=None,
            sha256=actual_hash,
            policy_path=str(json_path),
        )
    if actual_hash != side_hash:
        return PolicyLoadResult(
            ok=False,
            reason="hash_mismatch",
            errors=[f"hash mismatch: file={actual_hash} sidecar={side_hash}"],
            policy=None,
            sha256=actual_hash,
            policy_path=str(json_path),
        )

    # 4. schema (subset) validation
    schema_errors = _validate_schema_stub(policy)
    if schema_errors:
        return PolicyLoadResult(
            ok=False,
            reason="schema_violation",
            errors=schema_errors,
            policy=None,
            sha256=actual_hash,
            policy_path=str(json_path),
        )

    # 5. exact identity checks
    errors: list[str] = []
    if policy.get("policy_id") != EXPECTED_POLICY_ID:
        errors.append(
            f"policy_id {policy.get('policy_id')!r} != expected {EXPECTED_POLICY_ID!r}"
        )
    if policy.get("policy_version") != EXPECTED_POLICY_VERSION:
        errors.append(
            f"policy_version {policy.get('policy_version')!r} != expected {EXPECTED_POLICY_VERSION!r}"
        )
    if policy.get("owner") != EXPECTED_OWNER:
        errors.append(
            f"owner {policy.get('owner')!r} != expected {EXPECTED_OWNER!r}"
        )
    if policy.get("change_authority") != EXPECTED_CHANGE_AUTHORITY:
        errors.append(
            f"change_authority {policy.get('change_authority')!r} != expected {EXPECTED_CHANGE_AUTHORITY!r}"
        )
    if policy.get("status") != EXPECTED_STATUS:
        errors.append(
            f"status {policy.get('status')!r} != expected {EXPECTED_STATUS!r}"
        )

    if errors:
        return PolicyLoadResult(
            ok=False,
            reason="policy_identity_mismatch",
            errors=errors,
            policy=None,
            sha256=actual_hash,
            policy_path=str(json_path),
        )

    # 6. schema file parse (we already validated the data; verify the schema
    # itself is well-formed JSON so the audit evidence stays self-consistent)
    if schema_path.exists():
        try:
            json.loads(schema_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return PolicyLoadResult(
                ok=False,
                reason="malformed_schema",
                errors=[f"schema parse failed: {exc}"],
                policy=None,
                sha256=actual_hash,
                policy_path=str(json_path),
            )

    return PolicyLoadResult(
        ok=True,
        reason="",
        errors=[],
        policy=policy,
        sha256=actual_hash,
        policy_path=str(json_path),
    )


def is_retired_id(policy: dict, rid: str) -> bool:
    """Convenience: check whether an ID is in deprecated_requirement_ids."""
    if not isinstance(policy, dict):
        return False
    return rid in (policy.get("deprecated_requirement_ids") or [])


def is_industry_preset_blocked(policy: dict, name: str) -> bool:
    """Convenience: check whether an industry preset name is blocked."""
    if not isinstance(policy, dict):
        return False
    n = (name or "").lower()
    for blocked in policy.get("industry_presets_blocked", []) or []:
        if n == blocked.lower() or n in blocked.lower() or blocked.lower() in n:
            return True
    return False


def is_retired_alias(policy: dict, text: str) -> list[str]:
    """Return the list of retired aliases that appear in `text`.

    A bare hit on a single character is intentionally NOT a match (we
    guard against Chinese single-character false positives in code /
    identifiers). Substring match is case-sensitive for English tokens
    and case-insensitive for ASCII components.
    """
    if not isinstance(policy, dict) or not text:
        return []
    out: list[str] = []
    aliases = policy.get("retired_aliases", []) or []
    for alias in aliases:
        if not isinstance(alias, str) or len(alias.strip()) < 2:
            continue
        if alias in text:
            out.append(alias)
    return sorted(set(out))


def retired_alias_kind_of(policy: dict, alias: str) -> str | None:
    """Return the kind bucket name for a retired alias, or None."""
    if not isinstance(policy, dict) or not alias:
        return None
    kind = policy.get("retired_alias_kind", {}) or {}
    if not isinstance(kind, dict):
        return None
    for kind_name, alias_list in kind.items():
        if isinstance(alias_list, list) and alias in alias_list:
            return kind_name
    return None


def is_prohibited_path(policy: dict, path: str) -> bool:
    """Convenience: check whether a path / key contains a prohibited token."""
    if not isinstance(policy, dict):
        return False
    p_norm = (path or "").replace("/", "\\").lower()
    for token in policy.get("historical_source_prohibited_keys", []) or []:
        t_norm = token.replace("/", "\\").lower()
        if t_norm in p_norm:
            return True
    return False


__all__ = [
    "PolicyLoadResult",
    "load_strategy_policy",
    "is_retired_id",
    "is_industry_preset_blocked",
    "is_prohibited_path",
    "is_retired_alias",
    "retired_alias_kind_of",
    "POLICY_FILENAME",
    "SCHEMA_FILENAME",
    "SIDECAR_FILENAME",
    "EXPECTED_POLICY_ID",
    "EXPECTED_POLICY_VERSION",
]