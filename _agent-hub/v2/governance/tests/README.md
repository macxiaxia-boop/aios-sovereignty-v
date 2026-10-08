# governance/tests/ — read me first

> **Status:** R281.2 (2026-09-29). This directory contains TEST-ONLY artifacts.
> **No file here is canonical.** Do NOT read anything under this directory as
> protocol truth.

## What lives here

| Path | Purpose |
|---|---|
| `fixtures/TEST_ONLY_protocol_registry.json` | Fixture used by `protocol_registry.py` when invoked with `--registry <path>` for test isolation. Mirrors the schema but does NOT participate in `current_by_family` resolution. |

## Why this directory exists

The protocol registry validator/publisher (`protocol_registry.py`) accepts a
`--registry` flag so that tests can point it at a scratch JSON instead of the
real canonical file. To prevent leakage:

- The fixture filename is prefixed `TEST_ONLY_` and lives under `tests/fixtures/`.
- `CANONICAL_INDEX.json` / `PLACEMENT_RULES.md` / `PROTOCOL_AUDIT.md` all
  point to a SINGLE canonical registry: `governance/PROTOCOL_REGISTRY.json`.
- `protocol_registry.py` validates only the file passed via `--registry` (or
  the default canonical path). It does not scan `tests/fixtures/`.

## Rules

1. **NEVER** read a file under `governance/tests/` to resolve a "current"
   pointer. Always consult `governance/PROTOCOL_REGISTRY.json`.
2. **NEVER** add a `current` entry pointing into `governance/tests/`. The
   validator will reject such a path because tests/ is not on the canonical
   registry's lookup surface.
3. If you add a new fixture, prefix the filename with `TEST_ONLY_` and keep
   it under `fixtures/`. Do NOT add fixtures at the governance/ root.
4. Fixtures may be freely deleted; they are not part of the audit manifest.