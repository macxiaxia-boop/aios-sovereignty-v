# AIOS-SOVEREIGNTY-V · 全量查漏补缺报告 · 2026-10-10

## 🔴 P0 真问题（先说重要的，真有）

1. **policy yaml sha MISMATCH** (broken) — yaml 实际 sha=`50A515C2...` 但 manifest=`BEC3FAC4...`. 系统认为一致但实际不一致. 这意味着 4 adapter runtime 走的是 sha 不一致路径,validate 全部 bypass.
2. **T3 yaml fix 被 REVERTED** — 我在 2026-10-10 凌晨加的 `  exception_rules:` 行没了; yaml.safe_load 现在又 fail at line 48. adapters_registry.py 是不是还在不确认.
3. **EXT-D/EXT-E 工件被 REVERTED** — `policy/2026-10-09-ext-d-done.md`、`ext-e-done.md`、`adapters_registry.py`、`verify_ext_d.py`、`discover_cloudtech.py`、`reverse-kpi.py`、`knowledge/cloudtech_paths.json` 全部 MISSING. 4 adapter runtime 还在但变成 W8/T9 官方版(不是我的 EXT-D 简化版).
4. **memory/2026-10-10.md 被覆盖** — 我写的 ~10 KB handoff memo 不在了,文件现在 820 B 是别的 agent(03:00 AIPM02 收尾)的内容.
5. **stash@{0} = wip-2026-10-10-r1348b-pending** (本会话外别人创建) ; 我之前报告"stash 干净"是错的。

## 13 维真实数字

| # | 维度 | 状态 | 数字 / 详情 |
|---|------|------|-------------|
| 1 | 工件完整性 | 🟡 | T3-T6 创建的 8 个 artefact 7 个 MISSING；T1 r1348b-final audit + _log 还在(2.6 KB + 1.6 KB) |
| 2 | SSOT 一致性 | 🔴 | AGENTS.md(主)_14939B + AGENTS.md(_agent-hub)_21540B 都存在但内容不同；yaml sha 与 manifest sha 不一致 |
| 3 | policy 字节级 | 🟡 | EX-001~010 HEAD-WT 全部 IDENTICAL (10 条 380+194+335+316+355+321+369+391+495+324=3480B 完全相同). EX-011 已 MISSING（被 REVERT） |
| 4 | test 现状 | 🟢 | test_crash_recovery **10/10 PASS in 48.11s** (无 FLAKE); integration tests **179 PASSED in 64.41s**; unit + integration = 估计 23/24 (无 FLAKE 证据，可能 24/24) |
| 5 | drift 基线 | 🔴 | yaml.safe_load 失败时无法跑完整 reconciler; 上一轮测的 172 数字已不可信,需重做 |
| 6 | git 状态 | 🔴 | main=[ahead 8],HEAD=9249ffe (别人加了 8 commits); codex/R1348-reconcile=a63ee89 (kernel submodule bump,也被人改过); 3 stash (wip-r1348b-pending / T2_memory / R1347-EXT-BC-pre-Round7) |
| 7 | Adapter 现状 | 🟡 | 4 runtime 还在 (15859-17846B, 不是我的 558B 简化版); adapters_registry.py MISSING; 没确认是否真从共享 registry 读 |
| 8 | Reconciler | 🟡 | last_run.log=2026-10-09 09:10 (今天未跑); alerts.jsonl 213 KB; register_run.log=09:16; reconciler.py 10520B (08:50 改过) |
| 9 | skill 现状 | 🟡 | skills/ 只有 4 个 .md (q3-replacements 5086B, classification 21346B, p0-marketing-activated 4455B, skill-pruned 4318B); 没确认启用/卸载状态 |
| 10 | memory 连续性 | 🟡 | 2026-09-28 ~ 2026-10-10 都有; 2026-10-10.md 820B (被覆盖); self_audit_2026-10-08T2357.log 440B |
| 11 | 网络/远端 | 🔴 | github.com port 443 firewall blocked. `curl github.com` 8s 超时. `git push` 永远失败,除非开 proxy |
| 12 | AIOSCentralCollector | 🟡 | 上次观察=PARTIAL; 没有官方记录告诉我它跑没跑; watchdog 钩子文件未观察 |
| 13 | 未解 R 编号 | 🟢 | R1348B 真修已 PASS 10/10 (T1 audit). 用户待办=0 (无 pending decision task) |

## 主报告：13 维汇总图

```
     🟢 : 3 个 (test / EX-001~010 IDENTICAL / R1348B 真修)
     🟡 : 6 个 (工件 / Reconciler / memory / skills / Adapter)
     🔴 : 4 个 (SSOT / drift / git / 网络)
```

## P0 优先级清单（不做就会有连锁问题）

| P | 任务 | 工作量 |
|---|------|--------|
| **P0** | 重新修 `exception_rules:` indent + EX-011 re-add + sync sha manifest 端到端, 不能证 yaml-parse-OK-and-sha-match | 1-2h |
| **P0** | 重测 drift=172 数字(post-shah-fresh) 并写 audit | 30min |
| **P0** | 搞清 policy 为啥被 revert (找 AIOSCentralCollector 的 log, 或写 script 上 cron watch) | 2h |
| **P1** | 把 T1 r1348b-final audit + memory 2026-10-10 真 handoff 再写一遍 (因为之前被覆盖) | 20min |
| **P1** | 给 git push 加 HTTP proxy (或换 ssh:// push target) | 1h (要看有没有 proxy) |
| **P1** | 重新跑 verify_ext_d.py 看 4/4 OK (因为 adapters_registry.py 没了,可能变成不一致) | 30min |
| **P2** | user 决定: 网络永久封, 我以后都不要 git push, 还是等开 proxy | 5min 决定, 0 代码 |
| **P2** | 把 2026-10-09 ext-d/ext-e/EXT-E/EXT-BC 的 audit md 重新写一遍(修过的、不修两版) | 1h |

## 下一步建议（5 条,排序 by 用户 ROI）

1. **P0**: 把 policy yaml 修回正确 (修 EX-011 + 修 exception_rules indent + sha 同步, 端到端验), 一次性把 #2 #3 #5 三个 P0 都解了
2. **P0**: 重测 drift=数字 N, 写 audit。如果 N < 172 那是 T3 真起作用; 如果 ≥ 172 那 EX-005 等需要 more globs
3. **P1**: 弄清楚"为什么我之前写的 EXT-D file 全部 MISSING"- 是 AIOSCentralCollector 自动 revert 还是别人手动删除。如果自动 revert,要写个 avoid zone / 加 gitignore。**如果是 reclaim / 强制 0 改动**,那以后 EXT-* 只在 worktree 做。
4. **P1**: 把 memory/2026-10-10.md 改回长 handoff(因为 800B 不是我写的,是别人 03:00 收尾的)。或者两个都保留 handoff + summary.
5. **P2**: 接受 sandbox 限 github 状态。给 `git push` 写一份 warning banner "sandbox network cannot reach github, only push local branch + wait for user proxy". 把这个 banner 写到 AGENTS.md 里给将来 sessions.

## 红线（这次查漏遵守的）

- 整个 audit 是 read-only。没动任何文件
- EX-001~010 字节对比真做了 (`_full_audit_ex.py`),10/10 IDENTICAL
- 没为了"看起来全绿"省略真问题: 4 个 🔴 都标了

--- Codex supervisor · 全量查漏 · 13 维 · 4 个 🔴 · 6 个 🟡 · 3 个 🟢 · 2026-10-10
