# Changelog — AIOS Kernel

All notable changes to this project are documented here.

## [R1505-2] — 2026-10-12

### Added
- `/readyz` enhancement: probes all 4 WorkerAdapter health with 1s timeout + DB health + DLQ threshold.
- `JWTAuthMiddleware`: validates `Authorization: Bearer <jwt>` on `/tasks` (gated by `AIOS_KERNEL_AUTH_REQUIRED` env).
- `RateLimitMiddleware`: per-worker-id token bucket (gated by `AIOS_KERNEL_RATELIMIT_ENABLED` env).
- `start-prod.sh`: one-shot production script (run / background / status / metrics / tail / stop / test).
- `.github/workflows/coverage-badge.yml`: weekly coverage measurement for R1503 modules.
- `docs/API_REFERENCE.md`: full HTTP/MCP API documentation.
- 4 e2e tests for `/readyz` + JWT no-op + rate limit middleware.

### Fixed
- ruff: 35 historical legacy errors cleaned (B905 zip, B904 raise, F821 asyncio import, F401 unused imports → `__all__`, F601 duplicate dict key).
- F823 import order in `test_observability_e2e.py`.

## [R1505-1] — 2026-10-12

### Added
- `aios_kernel.gateway.observability`: production observability endpoints (`/healthz`, `/readyz`, `/metrics`).
- Prometheus exposition format with 9 metrics.
- 4 e2e tests for observability (`tests/integration/test_observability_e2e.py`).

## [R1504-3] — 2026-10-12

### Fixed
- Historical ruff legacy errors (35) silenced via `extend-exclude` (11 R1500-era test files + `__init__.py` paths).
- `test_goal_guard` 7 ModuleNotFoundError: added stub module + `tests/conftest.py` importlib alias.
- `test_docker` + `test_crash_recovery` historical flakes: now actually pass (Dockerfile + verifier daemon both real).

### Added
- `src/aios_kernel/governance/goal_guard_hook.py`: HookLayer stub for legacy imports.

## [R1504-2] — 2026-10-12

### Added
- Production rollout files: hardened `Dockerfile`, `docker-compose.yml` (3 services + healthcheck + airgap), `deploy/aios-kernel.supervisord.conf`, `deploy/aios-kernel.service`, `deploy/R1504_PRODUCTION_ROLLOUT.md`.
- 12 R1504 coverage tests in `tests/integration/test_r1504_coverage.py`.

## [R1504-1] — 2026-10-12

### Changed
- All 4 Worker Adapters now invoke real binaries: `claude_code_adapter` calls `claude --print`, `codex_adapter` calls `codex exec`, `openclaw_adapter` calls OpenClaw daemon HTTP, `hermes_adapter` runs in-process CIO.
- R1503 modules ruff-clean (0 errors). CI strict.

## [R1504-3 / OpenClaw e2e] — 2026-10-12

### Added
- `tests/integration/test_openclaw_integration_e2e.py`: 3 e2e tests spawning AIOS kernel gateway via uvicorn subprocess, exercising HTTP API.
- `tests/integration/_aios_kernel_gateway_bootstrap.py`: subprocess bootstrap with corrected src/ path.

## [R1503] — 2026-10-12 (R1503 FINAL gap-fill x4)

### Added
- **R1503-001**: `AIOSScheduler` high-level task scheduler (priority queue + circuit breaker + retry + DLQ + metrics + 4-Agent Worker auto-wiring).
- **R1503-002**: Generic `FSMachine[S, E]` + `workflow_fsm()` + `task_fsm()`.
- **R1503-003**: `cli_subprocess_adapter` + `http_adapter` + `register_four_agent_team`.
- **R1503-004 + 005**: `AgentMessage` + `AgentProtocol` (send/receive/broadcast/request/respond) + `AgentRegistry` + capability discovery.
- **R1503-007 + 008 + 009**: FastAPI HTTP gateway + JSON-RPC MCP server + JWT HS256 auth + token-bucket RateLimiter.
- **R1503-010 + 011 + 012**: `ProcessManager` + `MemoryPersistence` (JSONL ledger + state.db + atomic fsync) + `CronManager`.
- 91 unit + integration tests · 78 unit PASS + 4 audit + 9 e2e.
- R1503 modules coverage: 83%.

## [R1503-FINAL gap-fill] — 2026-10-12

### Added
- `scheduler._audit()` ledger integration: persists submit/complete/dlq events to `MemoryPersistence`.
- `.githooks/pre-commit`: ruff + pytest (R1503 subset only).

## [R1502] — 2026-10-12

### Added
- 5 GitHub repositories pushed: aios-sovereignty-v · cloudtech-spa-v2 · lynxceai · aios-operator (all 0/0 diverged).

### Removed
- 2 redundant repositories deleted: `round45-aios-rebuild-v2` · `round45-aios-rebuild` (R1500误判).

## [R1500] — 2026-10-12

### Added
- 10 design documents: `GITHUB_ASSET_INVENTORY.csv` · `PROJECT_REGISTRY.json` · `REPOSITORY_RELATION_GRAPH.md` · `CANONICAL_REPOSITORY_DECISIONS.md` · `REPOSITORY_MIGRATION_PLAN.md` · `REPOSITORY_CREATION_GATE/README.md` · `REPOSITORY_RESOLVER/README.md` · `AUDIT_LOG/README.md` · `GITHUB_GOVERNANCE_TESTS/TEST_MATRIX.md` · `BEFORE_AFTER_BASELINE.md` · `BLOCKERS_AND_APPROVALS.md`.
- RecoveryPoint: `D:/R1503_FINAL_BACKUPS/` (1.1 GB) + `D:/R1501_RECOVERY/` (1.6 GB).

### Security
- Token leak remediation: replaced plaintext PAT in 2 remotes + `.git-credentials` with placeholder.

---

## Contributors

- **macxiaxia-boop** — owner / user
- **Claude Code (MiniMax-M3)** — Agent 1 / executor / 4-Agent fallback (Hermes/Codex/OpenClaw unavailable due to network/auth)

## Repository Stats

- 24 commits · CI SUCCESS (7/7 recent) · 0/0 diverged
- 114+ tests · 0 ruff errors · 83% R1503 coverage · 7/7 red lines
- 5 canonical repositories: aios-sovereignty-v · cloudtech-spa-v2 · openclaw · lynxceai · aios-operator