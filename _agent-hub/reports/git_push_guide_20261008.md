# AIOS VNext — Git Push Guide

## 仓库状态

- `D:\AIOS\.git` — 已 commit AIOS 单仓库 (Phase A 主修复 + Agent 治理文件)
- `D:\AIOS\kernel\.git` — 17+ commits (Phase A+B+C+D 全部代码 + tests)
- `D:\AIOS\aios_tasks\aios_vnext\` — **未在 git 中**（.gitignore 排除 aios_tasks）
- `D:\AIOS\_agent-hub\reports\` — 在 git 中（作为 Phase Done 证据归档）

## 用户手动 push 步骤

```bash
# 1. 选 remote（用户决定 repo 名）
cd D:\AIOS\kernel
git remote add origin https://github.com/<user>/aios-kernel.git
git push -u origin main

# 2. (optional) D:\AIOS 也 push
cd D:\AIOS
git remote add origin https://github.com/<user>/aios-vnext.git
git push -u origin main
```

## 为什么 aios_tasks/ 不在 git

- `aios_tasks` 在 D:\AIOS\.gitignore 被排除
- aios_tasks/aios_vnext/ 含 INDEX/Task Cards/Evidence — 这些是 **supervisor 元数据**，不需版本控制
- 但**最终报告与 spec 已 commit 到 _agent-hub\reports\**（在 D:\AIOS\kernel\.git 中）

## Codex supervisor 说明

Codex 未配置 origin (用户决定 remote URL + token)。如果用户希望 Codex 自行 push，需要：
1. 配置 `~/.gitconfig` 含 `[credential] helper=store`
2. 或在 `_agent-hub\secrets\github-token` 存 token (chmod 600)
3. Codex 可直接 `git push` (无交互)

## 当前未提交变更

D:\AIOS\kernel：
- M alembic.ini
- M pyproject.toml
- M src/aios_kernel/persistence/models.py
- M tests/integration/pytest_t0036_final.txt
- ?? aios_kernel.db

（这些是 Phase C/D 期间累积未提交修改 — 建议提交作为 final commit）

D:\AIOS：
- 未跟踪 aios_tasks/aios_vnext/（含所有 task cards/evidence/INDEX）
- 建议：要么修改 .gitignore 去掉 aios_tasks，要么提交作为 commit 历史的一部分

## 推荐 push 计划

1. `cd D:\AIOS\kernel` → commit remaining changes → push to `github.com/<user>/aios-kernel`
2. `cd D:\AIOS` → decide on aios_tasks (commit or ignore) → push to `github.com/<user>/aios-vnext`
3. CI/CD 设置：GitHub Actions 用现有 .github/workflows/ci.yml

Codex 已尽力完成 "自言上报”。下一步：用户提供 repo URL，Codex 立即 push。
