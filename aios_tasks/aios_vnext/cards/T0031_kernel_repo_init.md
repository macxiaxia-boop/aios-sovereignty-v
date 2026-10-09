---
id: T0031
title: Kernel 仓库初始化 + 目录骨架
owner: CC
priority: P0
track: 3 — VNext Phase A
preconditions: [T0030]
estimated_minutes: 60
depends_on: [T0030]
blocks: [T0032, T0033, T0034, T0035, T0036, T0037]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## Scope (要做)
1. **新建仓库** `D:\AIOS\kernel\`（独立 git repo，不与现有 AIOS 共享 git 史）
   - `git init`
   - `git config user.name "AIOS Kernel Dev" && git config user.email "kernel@aios.local"`
   - 默认分支 `main`
   - 初始 commit "scaffold: aios vnext kernel"

2. **目录结构**（一次性创建）：
   ```
   D:\AIOS\kernel\
   ├── pyproject.toml          # Poetry 项目 + 依赖锁
   ├── README.md
   ├── alembic.ini             # DB migration 工具
   ├── docker-compose.yml       # PG + 可选 Temporal 本地开发
   ├── src/
   │   └── aios_kernel/
   │       ├── __init__.py
   │       ├── domain/         # Pydantic models (Goal, Task, Plan...)
   │       ├── persistence/     # SQLAlchemy ORM + Alembic
   │       ├── workflows/      # Durable execution (T0033)
   │       ├── workers/         # Worker Adapter 注册 (T0034)
   │       ├── verifier/       # Verifier 协议 (T0035)
   │       ├── api/            # FastAPI
   │       └── cli.py
   ├── tests/
   │   ├── unit/               # 单元测试
   │   ├── integration/        # 集成测试 (T0036/T0037 用)
   │   └── sim/                # 模拟测试 (T0040 用)
   ├── scripts/
   │   ├── run_kernel.sh
   │   ├── run_verifier.sh
   │   └── seed_test_data.py
   └── docs/
       ├── architecture.md
       └── acceptance_criteria.md  # 引用 T0030
   ```

3. **pyproject.toml 依赖**：
   - `fastapi`、`uvicorn[standard]`、`sqlalchemy[asyncio]`、`alembic`、`psycopg[binary]`、`pydantic>=2`、`pydantic-settings`、`pytest`、`pytest-asyncio`、`httpx`、`temporalio`（T0033 用）、`pyyaml`
   - dev: `black`、`ruff`、`mypy`、`coverage`

4. **CI 配置** `.github/workflows/ci.yml`（如未启用 GitHub Actions 则本地 `scripts/ci.sh`）：
   - ruff lint
   - mypy typecheck
   - pytest unit + integration
   - coverage report

5. **基线 commit**: 在 T0030 已冻结 `AIOS_VNEXT_BASELINE_v0` 的 D:\AIOS 主仓库基础上，**新建独立 kernel 仓库**——这是规格 §100 Wrap-not-Rewrite 的具体实施

## Out-of-scope (不要做)
- ❌ 不要把现有 AIOS 代码搬进 kernel（只对接，不并入）
- ❌ 不要创建 GitHub remote（本地先 Tortoise / 离线）
- ❌ 不要触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence）
- ❌ 不要触碰 `_agent-hub/memory/*`
- ❌ 不要安装 Docker（仅 docker-compose.yml 模板）

## Inputs (CC 必须先读)
- T0030 Acceptance Spec v0.1
- VNext Master Spec §28 + §100
- 10-03 memory log 中提到的现有 router / daemon 列表（仅识别可能 Wrap 的接口）

## Outputs (CC 必须产出)
1. `D:\AIOS\aios_tasks\aios_vnext\evidence\T0031_<ts>.md`
2. `D:\AIOS\kernel\` 完整目录树（含所有 .py / .toml / .ini / .yml / .md 空骨架）
3. 初始 git log 输出
4. `pip install -e .` 成功证据

## Evidence Requirements
- [ ] `D:\AIOS\kernel\` 存在且 git init 完成
- [ ] 目录结构与 §Scope 2 完全一致
- [ ] pyproject.toml 依赖锁文件存在
- [ ] `python -c "import aios_kernel"` 不报错
- [ ] `pytest --collect-only` 输出 0 收集（无测试，但应有）
- [ ] `git log --oneline` 至少 1 行
- [ ] `ruff check src/` 无错误
- [ ] 没有跨进 D:\AIOS\ 的写

## Exit Criteria
1. evidence 全部勾选
2. CC 把 status=Submitted 后等 Codex

## Rollback
1. `Remove-Item D:\AIOS\kernel -Recurse -Force`（仅当 T0031 失败且未与 Baseline 冲突）
2. 写 rollback log

## Time Budget
60 分钟

## Codex Acceptance Gate
Codex 独立验证:
1. 目录结构与 §Scope 2 diff = 0
3. `cd D:\AIOS\kernel && git log --oneline | wc -l` ≥ 1
4. `pip install -e .` 退出码 0
5. `pytest --collect-only` 不报错
全部通过 → status=Verified。