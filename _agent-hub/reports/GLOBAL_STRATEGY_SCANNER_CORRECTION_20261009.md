# Scanner correction contract

Claude Code, read D:\AIOS\_agent-hub\AGENTS.md and memory 2026-10-08/09. Independent verification found `policy.contamination_scanner.ContaminationScanner.scan_path()` only matches prohibited tokens in the path/name and does not inspect file content. Therefore a quarantined WorkBuddy file whose old strategy is in its contents but not its filename produces zero findings, violating the requirement that quarantine/archive references be classified.

Implement a bounded, safe correction:
- `scan_path()` must inspect readable text files (UTF-8/GBK fallback, size cap, skip binaries) and emit structured findings for retired IDs, prohibited asset paths, and blocked industry presets found in content. It must combine content evidence with the existing source classification: quarantine/archive/read-only -> ARCHIVED_REFERENCE; active loadable path -> ACTIVE_VIOLATION; unknown -> UNVERIFIED. Keyword remains auxiliary, never sole decision.
- Keep path-only behavior and all existing API compatibility. Do not scan outside caller-provided paths. Do not read secrets by extension or files under `.env`, `.key`, `.pem`, token files. Do not recurse by default.
- Add tests proving (1) a quarantined file with retired content is ARCHIVED_REFERENCE, (2) an active file with retired content is ACTIVE_VIOLATION, (3) binary/unknown source is UNVERIFIED or skipped, (4) content with no matching tokens yields no finding.
- Correct `policy/strategy_index.json` tests.evidence path to the real `reports/GLOBAL_STRATEGY_RETIREMENT_PHASE2_20261009_EVIDENCE.json` if it is wrong; do not modify model-policy or AGENTS.md.
- Run all strategy tests and write `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_SCANNER_CORRECTION_20261009_EVIDENCE.md/.json`. End with ACK and changed paths.
