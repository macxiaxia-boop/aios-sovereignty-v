"""contamination_scanner.py — Structured contamination scanner.

This module classifies paths / payloads against the active Strategy
Policy and emits one of four verdicts:

    ACTIVE_VIOLATION   — references a deprecated asset or retired
                         requirement AND is in an active / loadable
                         surface (must be blocked)
    ARCHIVED_REFERENCE — references a deprecated asset but in a
                         read-only / frozen / quarantine surface
                         (must NOT be blocked; classified for
                         visibility)
    FALSE_POSITIVE     — keyword hit that, after source / context
                         classification, is benign (e.g. a code
                         comment mentioning a deprecated id)
    UNVERIFIED         — could not classify with confidence

The scanner NEVER uses keyword-only blocking. Every classification
must cross-check at least one of:

  - source_classification   (active / dormant / archived / quarantine)
  - dependency_evidence     (does anything still load this?)
  - retired_id_evidence     (does the policy list this as deprecated?)
  - scope_match             (does the hit live inside a deprecated path?)

Each finding is structured (machine-readable) so the gate can produce
JSON evidence.

This is an internal classifier — it does NOT take any destructive
action on the filesystem.

Content-aware scanning (since correction 2026-10-09)
---------------------------------------------------
`scan_path()` now inspects readable text file CONTENT (in addition to
the path/name) for retired ids, blocked industry presets, and
prohibited asset path keys. Findings derived from content are combined
with source classification:

  quarantine / archive / read-only -> ARCHIVED_REFERENCE
  active loadable file             -> ACTIVE_VIOLATION
  unknown (file missing, unreadable,
            secret/binary/oversize) -> UNVERIFIED

Keyword presence is *auxiliary* evidence; the source classification
is the load-bearing signal. Path-only behavior is preserved for every
call shape the previous API supported; content inspection is opt-in
via file existence + size + extension gate (no caller change needed).

Safety rails (cannot be disabled by callers):
  - Single file only; never recurses into directories.
  - Size cap (default 1 MiB); larger files are skipped (UNVERIFIED).
  - Secret files (extension / filename pattern) are NEVER read.
  - Binary detection via NUL-byte probe in the first 4 KiB.
  - Encoding fallback: utf-8 -> utf-8-sig -> gbk -> latin-1.
"""
from __future__ import annotations

import hashlib
import os
import re
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------- Enums
class Classification(str, Enum):
    ACTIVE_VIOLATION = "ACTIVE_VIOLATION"
    ARCHIVED_REFERENCE = "ARCHIVED_REFERENCE"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    UNVERIFIED = "UNVERIFIED"


# Default source classifications; tests can override
SOURCE_CLASSIFICATIONS: dict[str, str] = {
    "ACTIVE": "active",
    "DORMANT": "dormant",
    "ARCHIVED": "archived",
    "QUARANTINE": "quarantine",
    "READ_ONLY": "read_only",
    "INERT": "inert",
}


# ---------------------------------------------------------------- Content-scan limits
#: Default cap for content scan (1 MiB). Larger files are skipped.
DEFAULT_CONTENT_MAX_BYTES: int = 1 * 1024 * 1024

#: Filename basenames that must NEVER be opened by the content scanner.
SECRET_BASENAMES: frozenset[str] = frozenset({
    ".env",
    ".envrc",
    "id_rsa",
    "id_ed25519",
    ".netrc",
    "credentials",
    "credentials.json",
    "secrets.json",
    "service-account.json",
})

#: File extensions that must NEVER be opened by the content scanner.
SECRET_EXTENSIONS: frozenset[str] = frozenset({
    ".env", ".key", ".pem", ".p12", ".pfx", ".keystore",
    ".token", ".secret", ".credentials",
})

#: Substring markers inside a basename that flag secret/token files.
SECRET_BASENAME_MARKERS: tuple[str, ...] = (
    "token",
    "secret",
    "password",
    "apikey",
    "api_key",
    "private_key",
)


# ---------------------------------------------------------------- Models
@dataclass
class Finding:
    """A single scanner finding (structured, machine-readable)."""

    finding_id: str
    classification: Classification
    path: str
    reason: str
    matched_token: str | None = None
    matched_id: str | None = None
    source_classification: str = "UNKNOWN"
    dependency_evidence: str = ""
    confidence: str = "HIGH"
    excerpt: str = ""
    line: int | None = None
    evidence_kind: str = "path"  # 'path' | 'content' | 'asset_manifest'
    ts: float = field(default_factory=lambda: time.time())

    def to_dict(self) -> dict:
        d = asdict(self)
        d["classification"] = self.classification.value
        return d


@dataclass
class ScanReport:
    """Aggregated scanner output."""

    findings: list[Finding] = field(default_factory=list)
    blocked_paths: list[str] = field(default_factory=list)
    scan_started: float = field(default_factory=lambda: time.time())
    scan_finished: float = 0.0
    items_scanned: int = 0

    def add(self, f: Finding) -> None:
        self.findings.append(f)
        if f.classification == Classification.ACTIVE_VIOLATION:
            if f.path not in self.blocked_paths:
                self.blocked_paths.append(f.path)

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {c.value: 0 for c in Classification}
        for f in self.findings:
            out[f.classification.value] += 1
        return out

    def to_dict(self) -> dict:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "blocked_paths": list(self.blocked_paths),
            "counts": self.counts(),
            "scan_started": self.scan_started,
            "scan_finished": self.scan_finished,
            "items_scanned": self.items_scanned,
        }


# ---------------------------------------------------------------- Source classifier
def _normalize(path: str) -> str:
    return path.replace("/", "\\").rstrip("\\")


def classify_source(path: str, *, quarantine_root: str | None = None,
                    archived_roots: list[str] | None = None) -> str:
    """Return one of SOURCE_CLASSIFICATIONS values for a path.

    The default heuristic:
      - any path under quarantine_root  -> 'quarantine'
      - any path under archived_roots   -> 'archived'
      - any path under _archived_*      -> 'archived'
      - any path under _backup*         -> 'archived'
      - any path under D:\\CloudTech-*  -> 'archived'  (per audit H-06)
      - any path under _quarantine      -> 'quarantine'
      - AIOS_SOURCE_OF_TRUTH_FINAL     -> 'read_only'
      - AIOS_RECONSTRUCTION            -> 'read_only'
      - _audit_reports                 -> 'read_only'
      - codex sessions archived        -> 'inert'
      - _out                           -> 'inert'
      - everything else                -> 'active'
    """
    p = _normalize(path).lower()

    if quarantine_root and _normalize(quarantine_root).lower() in p:
        return "quarantine"

    if archived_roots:
        for root in archived_roots:
            if _normalize(root).lower() in p:
                return "archived"

    # common markers
    markers = [
        r"\\_archived_",
        r"\\_backup",
        r"\\_backups",
        r"\\_schtasks_bak",
        r"\\_r\d+_",
        r"\\d:\\cloudtech",
        r"\\d:\\cloudtech-portable",
        r"\\d:\\cloudtech-vault",
        r"\\d:\\cloudtech-inbox",
        r"\\d:\\cloudtech-live-execution",
        r"\\_quarantine\\",
        r"\\aios_source_of_truth_final\\",
        r"\\aios_reconstruction\\",
        r"\\_audit_reports\\",
        r"\\_out\\",
        r"\\archived_sessions\\",
    ]
    for m in markers:
        if re.search(m, p):
            if "_quarantine" in m:
                return "quarantine"
            if "read_only" in m or "audit_reports" in m or "source_of_truth_final" in m or "reconstruction" in m:
                return "read_only"
            if "_out" in m or "archived_sessions" in m:
                return "inert"
            return "archived"

    return "active"


# ---------------------------------------------------------------- Token matcher
@dataclass
class TokenRule:
    """A token-to-policy mapping used by the matcher."""

    token: str
    token_kind: str  # 'requirement_id' | 'industry_preset' | 'path_keyword'
    matched_id: str | None = None  # canonical ID emitted in finding


def build_token_rules(policy: dict) -> list[TokenRule]:
    """Build the rule set from a loaded policy dict."""
    rules: list[TokenRule] = []
    for rid in policy.get("deprecated_requirement_ids", []) or []:
        rules.append(TokenRule(token=rid, token_kind="requirement_id", matched_id=rid))
    for preset in policy.get("industry_presets_blocked", []) or []:
        rules.append(TokenRule(token=preset, token_kind="industry_preset", matched_id=preset))
    for key in policy.get("historical_source_prohibited_keys", []) or []:
        # lowercase keyword form for path matching
        rules.append(TokenRule(token=key, token_kind="path_keyword", matched_id=key))
    return rules


def build_content_token_set(policy: dict) -> list[str]:
    """Build the token set used for in-file content scanning.

    Content tokens are case-insensitive substring matches in file bodies.
    They include:

      - deprecated_requirement_ids (e.g. 'R-001')
      - industry_presets_blocked   (e.g. 'industry-zhuangxiu')
      - retired_aliases            (e.g. '医美', '装企', 'CloudTech V22')
        (correction 2026-10-09)
      - historical_source_prohibited_keys (paths / unique markers)
      - distinctive substrings extracted from prohibited_active_assets
        summaries (e.g. '127.0.0.1:5099', 'D:\\AIOS\\cloudtech-saas')

    Path-keyword tokens are path-only and NOT used for content matches.

    Aliases that are too short (<2 chars after strip) or that look like
    bare generic English words ('AI', 'SaaS', 'marketing', 'industry')
    are NEVER added; the policy must contain only distinctive,
    evidence-backed aliases.
    """
    tokens: list[str] = []
    seen: set[str] = set()

    def _add(tok: str) -> None:
        if not tok:
            return
        norm = tok.strip()
        if not norm or norm in seen:
            return
        seen.add(norm)
        tokens.append(norm)

    for rid in policy.get("deprecated_requirement_ids", []) or []:
        _add(str(rid))

    for preset in policy.get("industry_presets_blocked", []) or []:
        _add(str(preset))

    for alias in policy.get("retired_aliases", []) or []:
        if not isinstance(alias, str):
            continue
        s = alias.strip()
        # Refuse generic single-character or super-short hits that
        # would flood the gate. Distinctive aliases are at least 2
        # chars and contain either non-ASCII (CJK) or non-trivial
        # ASCII structure (sk-, V22, etc.).
        if len(s) < 2:
            continue
        _add(s)

    for key in policy.get("historical_source_prohibited_keys", []) or []:
        _add(str(key))

    # Extract distinctive substrings from prohibited_active_assets.
    # We look for: paths (D:\... or C:\...), IPs (x.x.x.x:port),
    # service names (long alphanumeric tokens), and bracketed ids.
    _re_path = re.compile(r"[A-Za-z]:\\[^\s,;\"'<>|\r\n\t]+")
    _re_ip_port = re.compile(r"\d{1,3}(?:\.\d{1,3}){3}:\d{2,5}")
    for asset in policy.get("prohibited_active_assets", []) or []:
        if not isinstance(asset, dict):
            continue
        for field_name in ("summary", "path", "quarantine_target"):
            txt = asset.get(field_name)
            if not txt:
                continue
            for m in _re_path.findall(str(txt)):
                _add(m)
            for m in _re_ip_port.findall(str(txt)):
                _add(m)

    return tokens


# ---------------------------------------------------------------- File-content helpers
def _is_secret_path(path: str) -> bool:
    """Return True iff `path` matches a secret-extension / secret-name rule.

    The scanner never opens these. Conservative: any basename that contains
    one of the well-known markers also refuses.
    """
    p = Path(path)
    name = p.name.lower()
    if not name:
        return False
    # basename-only blocks (e.g. '.env')
    base = name
    if base in SECRET_BASENAMES:
        return True
    # extension blocks
    suffix = p.suffix.lower()
    if suffix in SECRET_EXTENSIONS:
        return True
    # substring markers anywhere in the basename
    for marker in SECRET_BASENAME_MARKERS:
        if marker in base:
            return True
    return False


def _looks_binary(sample: bytes) -> bool:
    """Conservative binary detector: any NUL byte in the first 4 KiB."""
    if not sample:
        return False
    return b"\x00" in sample[:4096]


def _decode_text(raw: bytes) -> str | None:
    """Try to decode `raw` as text. Returns None on decode failure."""
    for enc in ("utf-8", "utf-8-sig", "gbk", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return None


def read_file_text_safely(path: str, *, max_bytes: int = DEFAULT_CONTENT_MAX_BYTES) -> tuple[str | None, str]:
    """Read a file as text with safety rails. Returns (text | None, reason).

    Reasons on success: 'ok'.
    Reasons on refusal: 'missing', 'not_a_file', 'too_large', 'secret',
    'binary', 'unreadable', 'decode_failed'.
    """
    try:
        st = os.stat(path)
    except OSError:
        return None, "missing"
    if not (st.st_mode & 0o170000 == 0o100000):  # not a regular file (covers dirs, symlinks loosely)
        # pathlib treats symlinks to files as regular files; we accept symlinks
        # to files but refuse directories.
        pass
    if os.path.isdir(path):
        return None, "not_a_file"
    if _is_secret_path(path):
        return None, "secret"
    if st.st_size > max_bytes:
        return None, "too_large"
    try:
        with open(path, "rb") as fh:
            raw = fh.read(max_bytes + 1)
    except OSError:
        return None, "unreadable"
    if len(raw) > max_bytes:
        raw = raw[:max_bytes]
    if _looks_binary(raw):
        return None, "binary"
    text = _decode_text(raw)
    if text is None:
        return None, "decode_failed"
    return text, "ok"


# ---------------------------------------------------------------- Scanner
class ContaminationScanner:
    """Classify paths/payloads against a loaded strategy policy."""

    def __init__(
        self,
        policy: dict,
        *,
        quarantine_root: str | None = None,
        archived_roots: list[str] | None = None,
        scan_active_assets: list[dict] | None = None,
        max_content_bytes: int = DEFAULT_CONTENT_MAX_BYTES,
    ) -> None:
        self.policy = policy
        self.quarantine_root = quarantine_root
        self.archived_roots = archived_roots or []
        self.rules: list[TokenRule] = build_token_rules(policy)
        self.content_tokens: list[str] = build_content_token_set(policy)
        self.scan_active_assets: list[dict] = scan_active_assets or []
        self.max_content_bytes = max_content_bytes

    # ----- Public API
    def scan_path(self, path: str) -> list[Finding]:
        """Classify a single path.  Returns 0..N findings (may be 0 if clean).

        Combines three inspection layers:
          1. Path / name keyword match (existing path-only behaviour)
          2. Active-asset manifest match (existing)
          3. File CONTENT keyword match (new, opt-in by file existence)

        Content findings respect safety rails: no recursion, secrets
        refused, binary / oversize skipped, encoding fallback handled.
        """
        out: list[Finding] = []
        src_class = classify_source(
            path,
            quarantine_root=self.quarantine_root,
            archived_roots=self.archived_roots,
        )

        # Layer 1: Path-keyword rules
        for rule in self.rules:
            if rule.token_kind == "path_keyword":
                token_norm = rule.token.replace("/", "\\").lower()
                if token_norm in path.replace("/", "\\").lower():
                    out.append(self._classify_path_keyword_hit(path, rule, src_class))
            elif rule.token_kind == "requirement_id":
                # Check if path contains the retired R-NNN token.  We use a
                # simple substring match (with literal boundary chars) because
                # `\b` doesn't recognize `-` as a word boundary in regex.
                if rule.token in path:
                    out.append(self._classify_path_keyword_hit(path, rule, src_class))
            elif rule.token_kind == "industry_preset":
                if rule.token.lower() in path.lower():
                    out.append(self._classify_path_keyword_hit(path, rule, src_class))

        # Layer 2: Active-asset manifest
        for asset in self.scan_active_assets:
            asset_id = (asset.get("id") or "").upper()
            target_path = asset.get("path") or asset.get("summary") or ""
            if not target_path:
                continue
            if not self._path_contains_target(path, target_path):
                continue
            rule = TokenRule(token=target_path, token_kind="path_keyword", matched_id=asset_id)
            out.append(self._classify_path_keyword_hit(path, rule, src_class))

        # Layer 3: File CONTENT keyword match (correction 2026-10-09).
        # Only invoked for an actual file on disk; never recurses.
        content_findings = self._scan_file_content(path, src_class)
        out.extend(content_findings)

        return out

    def scan_text(self, text: str, *, surface: str = "<text>") -> list[Finding]:
        """Classify a payload text."""
        out: list[Finding] = []
        for rule in self.rules:
            if rule.token_kind == "path_keyword":
                continue
            if rule.token and rule.token in (text or ""):
                out.append(self._classify_text_hit(surface, rule))
        return out

    def scan_payload(self, payload: dict, *, surface: str = "<payload>") -> list[Finding]:
        """Classify a structured payload (e.g. an envelope)."""
        return self.scan_text(json.dumps(payload, ensure_ascii=False) if payload else "", surface=surface)

    # ----- Internals
    def _scan_file_content(self, path: str, src_class: str) -> list[Finding]:
        """Inspect the file at `path` for policy tokens.

        Returns content-derived findings only. The caller must combine
        with path-derived findings. Refusal paths emit zero findings
        (per the contract: 'binary/unknown source is UNVERIFIED or
        skipped').

        If the file exists and was successfully read but contained no
        matching tokens, returns []. If the file did not exist or could
        not be read, returns []. The caller is responsible for emitting
        UNVERIFIED findings on a separate signal — but we never want to
        spam UNVERIFIED for every active file we read.
        """
        text, reason = read_file_text_safely(path, max_bytes=self.max_content_bytes)
        if text is None:
            return []
        if not self.content_tokens:
            return []

        out: list[Finding] = []
        lower = text.lower()
        for tok in self.content_tokens:
            tok_lower = tok.lower()
            if tok_lower and tok_lower in lower:
                out.append(self._classify_content_hit(path, tok, src_class))
        return out

    def _classify_path_keyword_hit(self, path: str, rule: TokenRule, src_class: str) -> Finding:
        fid = self._new_finding_id(path, rule.matched_id or rule.token, "path")
        if src_class in ("quarantine", "archived"):
            return Finding(
                finding_id=fid,
                classification=Classification.ARCHIVED_REFERENCE,
                path=path,
                reason=f"references prohibited token {rule.matched_id or rule.token!r} but lives in {src_class} surface",
                matched_token=rule.token,
                matched_id=rule.matched_id,
                source_classification=src_class,
                confidence="HIGH",
                evidence_kind="path",
            )
        if src_class in ("read_only", "inert", "dormant"):
            return Finding(
                finding_id=fid,
                classification=Classification.ARCHIVED_REFERENCE,
                path=path,
                reason=f"references prohibited token {rule.matched_id or rule.token!r} in {src_class} surface (no runtime loader)",
                matched_token=rule.token,
                matched_id=rule.matched_id,
                source_classification=src_class,
                confidence="HIGH",
                evidence_kind="path",
            )
        # active surface but keyword hit
        return Finding(
            finding_id=fid,
            classification=Classification.ACTIVE_VIOLATION,
            path=path,
            reason=f"active surface references prohibited token {rule.matched_id or rule.token!r}",
            matched_token=rule.token,
            matched_id=rule.matched_id,
            source_classification=src_class,
            confidence="MEDIUM",
            evidence_kind="path",
        )

    def _classify_content_hit(self, path: str, token: str, src_class: str) -> Finding:
        """Classify a content-derived hit using source classification.

        - quarantine/archive/read_only/inert/dormant -> ARCHIVED_REFERENCE
        - active loadable file                       -> ACTIVE_VIOLATION
        - 'active' surface but path-not-on-disk OR
          content read refused                       -> UNVERIFIED
        """
        fid = self._new_finding_id(path, token, "content")
        if src_class in ("quarantine", "archived", "read_only", "inert", "dormant"):
            return Finding(
                finding_id=fid,
                classification=Classification.ARCHIVED_REFERENCE,
                path=path,
                reason=f"file content references prohibited token {token!r} in {src_class} surface (no runtime loader)",
                matched_token=token,
                matched_id=token,
                source_classification=src_class,
                confidence="HIGH",
                evidence_kind="content",
            )
        # src_class is 'active' (default). Distinguish loadable vs unknown.
        # If the file isn't actually on disk, we can't confirm loadable.
        if not os.path.isfile(path):
            return Finding(
                finding_id=fid,
                classification=Classification.UNVERIFIED,
                path=path,
                reason=f"file content references prohibited token {token!r} but path is not a loadable file",
                matched_token=token,
                matched_id=token,
                source_classification=src_class,
                confidence="LOW",
                evidence_kind="content",
            )
        return Finding(
            finding_id=fid,
            classification=Classification.ACTIVE_VIOLATION,
            path=path,
            reason=f"active loadable file content references prohibited token {token!r}",
            matched_token=token,
            matched_id=token,
            source_classification=src_class,
            confidence="HIGH",
            evidence_kind="content",
        )

    def _classify_text_hit(self, surface: str, rule: TokenRule) -> Finding:
        fid = self._new_finding_id(surface, rule.matched_id or rule.token, "text")
        # text hits default to UNVERIFIED unless source context known
        if rule.token_kind == "requirement_id":
            return Finding(
                finding_id=fid,
                classification=Classification.UNVERIFIED,
                path=surface,
                reason=f"text references retired requirement id {rule.matched_id}",
                matched_token=rule.token,
                matched_id=rule.matched_id,
                source_classification="text",
                confidence="LOW",
                evidence_kind="path",
            )
        if rule.token_kind == "industry_preset":
            return Finding(
                finding_id=fid,
                classification=Classification.ACTIVE_VIOLATION,
                path=surface,
                reason=f"text references blocked industry preset {rule.matched_id}",
                matched_token=rule.token,
                matched_id=rule.matched_id,
                source_classification="text",
                confidence="MEDIUM",
                evidence_kind="path",
            )
        return Finding(
            finding_id=fid,
            classification=Classification.UNVERIFIED,
            path=surface,
            reason=f"text token match {rule.matched_id or rule.token}",
            matched_token=rule.token,
            matched_id=rule.matched_id,
            source_classification="text",
            confidence="LOW",
            evidence_kind="path",
        )

    def _path_contains_target(self, path: str, target: str) -> bool:
        p = _normalize(path).lower()
        t = _normalize(target).lower()
        return t in p

    @staticmethod
    def _new_finding_id(path: str, token: str | None, evidence_kind: str) -> str:
        h = hashlib.sha256(
            f"{evidence_kind}|{path}|{token or ''}".encode("utf-8")
        ).hexdigest()[:12].upper()
        return f"SCAN-{h}"


# ---------------------------------------------------------------- Quarantine allowlist
def is_quarantined_path(path: str, quarantine_root: str) -> bool:
    """Return True iff `path` lives inside `quarantine_root`."""
    if not quarantine_root:
        return False
    p = _normalize(path).lower()
    q = _normalize(quarantine_root).lower()
    return p.startswith(q)


__all__ = [
    "Classification",
    "SOURCE_CLASSIFICATIONS",
    "Finding",
    "ScanReport",
    "ContaminationScanner",
    "classify_source",
    "build_token_rules",
    "build_content_token_set",
    "read_file_text_safely",
    "is_secret_path",
    "DEFAULT_CONTENT_MAX_BYTES",
    "SECRET_BASENAMES",
    "SECRET_EXTENSIONS",
    "is_quarantined_path",
]