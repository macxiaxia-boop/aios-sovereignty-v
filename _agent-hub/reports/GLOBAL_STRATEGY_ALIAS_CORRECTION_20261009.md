# Strategy alias correction contract

Claude Code, read D:\AIOS\_agent-hub\AGENTS.md and memory 2026-10-08/09. Independent verification found the policy/gate blocks synthetic IDs such as `industry-zhuangxiu`, but the actual quarantined WorkBuddy memory contains Chinese aliases `医美`, `装企`, `行业垂直`, `灵策智算`, `灵策AI`, and old CloudTech/V22 wording. `scan_text` returns no finding for that real file, and a task mentioning `医美+装企` can evade the gate.

Implement the smallest evidence-backed correction:
- Add a structured `retired_aliases` list to the single product strategy policy (and schema/loader validation if needed), containing only aliases proven in the audit/real quarantined asset: Chinese industry names/old positioning terms, old CloudTech/V22/V23 product terms, old skill identifiers (`sk-industry`, `sk-cross-matrix`), and the old vertical workflow/pipeline terms. Do not add generic words like `industry`, `marketing`, `AI`, `SaaS`, or unrelated false positives.
- Update StrategyGate so aliases are checked in structured task fields and text, combined with retired IDs/assets/source context; do not make a bare keyword the only decision. Emit STRATEGY_DRIFT_DETECTED or DEPRECATED_ASSET_REFERENCED as appropriate and preserve policy hash/fail-closed behavior.
- Update ContaminationScanner so real file content containing these aliases is classified by source: quarantine/archive -> ARCHIVED_REFERENCE, active loadable -> ACTIVE_VIOLATION, unknown -> UNVERIFIED; preserve binary/secret/size guards.
- Update SHA sidecar/schema/index only as required by the policy change. Add tests using the actual quarantined memory file and a synthetic active file/task containing `医美+装企`; add false-positive tests for generic `industry`/`SaaS`/`AI`.
- Run all strategy tests and write `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_ALIAS_CORRECTION_20261009_EVIDENCE.md/.json`. Do not touch services, backups, product code, AGENTS.md, model-policy, or git history. End with ACK.
