"""snapshot.py — ModelPolicy v1 YAML loader + ed25519 verifier.

Reads model-policy.v1.yaml, verifies sha256 + ed25519 signature,
returns PolicySnapshot dataclass.
"""
from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict

import yaml
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


@dataclass(frozen=True)
class PolicySnapshot:
    """Loaded ModelPolicy v1."""
    policy_id: str
    sha256: str
    sig_ed25519: str
    created_at: datetime
    created_by: str
    authorizer: str
    schema_version: str
    status: str
    allowlist: List[str] = field(default_factory=list)
    denylist: List[str] = field(default_factory=list)
    optional: List[str] = field(default_factory=list)
    providers: List[dict] = field(default_factory=list)
    enforcement: dict = field(default_factory=dict)
    credential_sync: dict = field(default_factory=dict)
    governance: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict)


def _yaml_str(obj) -> str:
    """Stable YAML serialization (sort_keys=True for hash stability)."""
    return yaml.safe_dump(obj, sort_keys=True, default_flow_style=False, allow_unicode=True)


def compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def serialization_load_openssh_public(pem_bytes: bytes) -> Ed25519PublicKey:
    from cryptography.hazmat.primitives.serialization import load_ssh_public_key
    return load_ssh_public_key(pem_bytes)


def verify_signature(yaml_path: Path, pub_key_path: Path) -> bool:
    """Verify ed25519 signature on model-policy.v1.yaml.

    The signature signs the SHA256 of the canonical YAML text. After
    signing, the signature field is populated. To make verification
    work, we strip the signature.value field, recompute canonical text,
    compute SHA, then verify.
    """
    raw = Path(yaml_path).read_text(encoding="utf-8")
    parsed = yaml.safe_load(raw)
    sig_b64 = (parsed.get("signature") or {}).get("value", "")
    if not sig_b64 or "PENDING" in sig_b64:
        return False
    sig = base64.b64decode(sig_b64)
    pub_pem = Path(pub_key_path).read_bytes()
    pub = serialization_load_openssh_public(pub_pem)

    # Re-canonicalize WITHOUT signature.value
    parsed_for_hash = dict(parsed)
    sig_dict = dict(parsed_for_hash.get("signature") or {})
    sig_dict["value"] = "REDACTED"
    parsed_for_hash["signature"] = sig_dict
    canonical = _yaml_str(parsed_for_hash).encode("utf-8")
    sha = compute_sha256(canonical).encode()
    try:
        pub.verify(sig, sha)
        return True
    except Exception:
        return False


def load_policy(yaml_path: Path, pub_key_path: Optional[Path] = None) -> PolicySnapshot:
    """Load + verify policy from YAML file."""
    raw = Path(yaml_path).read_text(encoding="utf-8")
    parsed = yaml.safe_load(raw)

    if pub_key_path is not None and pub_key_path.exists():
        sig_ok = verify_signature(yaml_path, pub_key_path)
        if not sig_ok:
            raise ValueError(
                f"Signature verification failed for {yaml_path}. "
                f"Refusing to load untrusted policy."
            )

    allowlist_data = parsed.get("allowlist", {})
    denylist_raw = allowlist_data.get("denylist", [])
    optional_raw = allowlist_data.get("optional", [])

    return PolicySnapshot(
        policy_id=parsed.get("policy_id", "unknown"),
        sha256=compute_sha256(raw.encode("utf-8")),
        sig_ed25519=(parsed.get("signature") or {}).get("value", ""),
        created_at=_parse_dt(parsed.get("created_at", "")),
        created_by=parsed.get("created_by", "unknown"),
        authorizer=parsed.get("authorizer", "unknown"),
        schema_version=parsed.get("schema_version", "unknown"),
        status=parsed.get("status", "DRAFT"),
        allowlist=_flatten_models(allowlist_data.get("providers", [])),
        denylist=[d["id"] for d in denylist_raw if "id" in d],
        optional=[d["id"] for d in optional_raw if "id" in d],
        providers=allowlist_data.get("providers", []),
        enforcement=parsed.get("enforcement", {}),
        credential_sync=parsed.get("credential_sync", {}),
        governance=parsed.get("governance", {}),
        raw=parsed,
    )


def _parse_dt(s: str) -> datetime:
    if not s:
        return datetime.fromtimestamp(0)
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return datetime.fromtimestamp(0)


def _flatten_models(providers: List[dict]) -> List[str]:
    """Flatten providers[].models[].id into a single allowlist."""
    out = []
    for p in providers:
        for m in p.get("models", []):
            mid = m.get("id") if isinstance(m, dict) else m
            if mid:
                out.append(mid)
    return out


def sign_yaml(yaml_path: Path, priv_key_path: Path) -> str:
    """Sign YAML file with ed25519 private key. Returns base64 signature.

    Workflow:
    1. Read YAML, parse
    2. Insert signature.value=REDACTED placeholder
    3. Serialize to canonical YAML text
    4. Compute SHA256 of canonical text
    5. Sign SHA256 with priv
    6. Replace REDACTED with actual signature
    7. Write final YAML back
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    priv_bytes = Path(priv_key_path).read_bytes()
    priv = Ed25519PrivateKey.from_private_bytes(priv_bytes)

    raw = Path(yaml_path).read_text(encoding="utf-8")
    parsed = yaml.safe_load(raw)

    parsed.setdefault("signature", {})
    parsed["signature"]["alg"] = "ed25519"
    parsed["signature"]["value"] = "REDACTED"
    parsed["signature"]["public_key_path"] = str(priv_key_path).replace(".key", ".pub")
    parsed["status"] = "SIGNED"

    canonical = _yaml_str(parsed).encode("utf-8")
    sha = compute_sha256(canonical).encode()
    sig = priv.sign(sha)
    sig_b64 = base64.b64encode(sig).decode()

    # Replace REDACTED with actual signature
    parsed["signature"]["value"] = sig_b64
    final_text = _yaml_str(parsed)
    Path(yaml_path).write_text(final_text, encoding="utf-8")
    return sig_b64
