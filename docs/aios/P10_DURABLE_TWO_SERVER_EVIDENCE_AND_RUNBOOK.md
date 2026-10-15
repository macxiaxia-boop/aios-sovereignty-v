# P10｜AIOS × CloudTech 双服务真实调用与持久恢复验收

2026-10-14，延续原有 AIOS PR #3 和 CloudTech PR #1。本文件是**当前源码对应的实测证据与本地续航操作指令**，不是新的大框架，不代表业务所有功能验收。

## 1. 真正已经落地的运行链路

```
AIOS FastAPI Gateway /tasks (JWT tenant identity)
  -> existing AIOSScheduler
     -> optional SQLite DurableDispatchStore (commit-before-202)
        -> atomic SQL claim + fencing token + lease heartbeat
           -> explicit WorkerRegistry CloudTechV4Adapter
              -> CloudTech real loopback FastAPI api.v4.asgi
                 -> GET /v4/workpaths/<path_id>/preflight
                 -> POST /v4/workpaths/runs (tenant-scoped idempotency)
                 -> POST /v4/workpaths/runs/<run_id>/execute-local
                    -> V4Orchestrator -> real url.normalize operation
                    -> stop at platform.permission_check [MOCK_ONLY]
           <- real ArtifactType.JSON (SHA-256 and task/run identity)
        <- SQLite committed worker artifact and final state
  <- GET /tasks/<run_id>/result (JWT tenant matches, business_validated=false)
```

**所有平台 API、付费生图、发帖、批量社媒抓取均未触发。** 得到的是现有工作流的一个真实确定性前缀，不是完整商业视频成品。

## 2. GitHub Actions 真证据

- 在 AIOS PR #3 的 commit `93fe163627d00840a2016002bfcb502a4318d075` 对应工作流运行 `38511946394`：Python 3.11/3.12/3.13、lint、quality gate 和 `Real AIOS↔CloudTech loopback HTTP` 全部通过。
- 这个跨仓库 smoke job 自己 checkout 现有 CloudTech PR 分支，以独立子进程启动 CloudTech V4，然后启动独立 AIOS Gateway 服务，用 Bearer JWT 创建 CloudTech 本地执行任务，读取完整 Artifact；停止、重新启动 AIOS 进程并用同一 run_id 读回 JSON；另一租户 JWT 返回 404。
- `tests/integration/test_p10_durable_dispatch.py` 包含 durable enqueue、SQLite 双连接原子认领、fencing 检查、只读预检安全恢复、非只读不确定结果隔离、重建调度器后结果保持，共 5 项测试。
- 后续安全收紧又补了任务提交 JWT tenant 匹配、任务状态租户校验、path_id/tenant_id 格式限制；以最新 HEAD CI 为最终判定，旧绿灯不可冒充新 HEAD 绿灯。

## 3. 对 3,920 项功能的直接作用

目前从“只有模块定义”真正进入 **一个业务路径的真实执行记录**。P8 的 73 组与 3,920 原始目录对象保持研究与施工台账，不能把它们误写为生产能力。CloudTech 原有六条 V4 工作路径 50 个静态定义节点还没有完全连上 Provider。

各功能项拆到下列不可省略字段，交给 Codex 检查：

`source_id → business_goal → path_id → node_id → required_input_ref → previous_artifact_ref → operation_id → real_adapter_location → tenant_scope → permission_and_budget_gate → idempotency_key → lease_fencing → output_ref → proof_hash → error_class → verifier → progress_state`。

每个节点必须用 P8 的分组明细关联真实源代码与测试；未接入真实 Provider 的节点保持 Mock/Unmapped/Blocked，而不是套一份模版。

## 4. 当前确定边界

1. SQLite 持久调度是 **显式开启的 opt-in 模式**：通过 `AIOS_SCHEDULER_SQLITE_PATH` 指定一个本机持久 DB 文件。默认已有内存调度模式不被强制变更。
2. 数据库 claim 和 fencing 支持多个 SQLite 连接争抢；不是所有远端 Provider 的 fencing enforcement。只能认为提交、领取、状态和 Artifact 持久化已经实现。
3. **重启后的只读 preflight**可自动重新排队。遇到在途 `create_and_execute_local` 等非完全只读操作，在租约超期后标为 `blocked_uncertain`，禁止自动重复调用外部动作。需要独立对账和人工确认后决定。
4. 当前还没有 Windows 实机运行验证，也没有真实 PostgreSQL 两节点进程 kill/恢复验收。
5. CloudTech V4 原始运行态仍基于内存 `V4Orchestrator`。AIOS SQLite 持久数据只能保证 AIOS 任务一侧，不可冒充 CloudTech 自身持久化完成。
6. CloudTech 前端缺失 Lynxce 页面源码导致 Lighthouse 失败。此前仅解决 V4 业务 API 的执行与安全性，不代表 UI 功能完成。
7. 工程 PR 保持 Draft，不合并、不部署公网、不发布社媒、不消耗付费额度、不删除。

## 5. Windows 本机联调命令（仅本机测试）

前提：原有两个仓库检出同一批 Draft PR 对应代码，已安装各自必要依赖；以既有 Windows 管理工具确认 Python 虚拟环境，不混用不同项目环境。

CloudTech PowerShell：

```powershell
cd <CloudTech本机已有仓库目录>
$env:V4_ENV = 'development'
python -m uvicorn api.v4.asgi:app --host 127.0.0.1 --port 5089
```

AIOS PowerShell（另一个窗口）：

```powershell
cd <AIOS本机已有仓库目录>
$env:CLOUDTECH_V4_BASE_URL = 'http://127.0.0.1:5089'
$env:CLOUDTECH_V4_GATEWAY_ENABLED = '1'
$env:AIOS_SCHEDULER_SQLITE_PATH = '.\runtime\scheduler.sqlite3'
$env:AIOS_KERNEL_AUTH_REQUIRED = '1'
$env:AIOS_KERNEL_RATELIMIT_ENABLED = '1'
# 本机密钥管理工具安全注入 AIOS_KERNEL_JWT_SECRET (至少 32 bytes)
# 不写进 git、脚本、日志、Excel 或 ChatGPT。
python -m uvicorn aios_kernel.gateway.serve:app --host 127.0.0.1 --port 5090
```

使用合法签发的带 `tenant_id` Claim 的 JWT 访问 `POST /tasks` 创建限权任务（参考 `P9_CLOUDTECH_WORKER_LIVE_LOCAL_HANDBOOK.md`）；然后用同一 JWT 读取 `GET /tasks/<id>/result`。检查 `state=completed`、`artifact.data.local_execution.status=PARTIAL`、`business_validated=false`、`blocked_at.reason=MOCK_ONLY`。停止/重启 AIOS，确认同一 id 仍返回同一哈希产物；换 tenant 的 JWT 必须 404。

## 6. 收口次序（不可凭进度自动变绿）

A. 使用真实 Windows AIOS 与真实 CloudTech 本机服务完成上述命令、截图、日志/数据库记录的验收。

B. AIOS Scheduler Queue 和 P7 WorkflowEngine Checkpoints 统一 lease/fencing 与外部 effect journal；尤其对生产引擎版本/取消/付款/发布引入幂等对账。不准宣称端到端恰好执行一次。

C. CloudTech V4 内存任务状态升级到与 AIOS 相协调的持久状态，支持真实重启和跨版本灰度；完成多租户身份、参数哈希与异地服务认证。

D. 恢复缺失 Lynxce 实际页面源码或根据既有真实产品蓝图实现完整页面、业务表单、API 调用、交互与真实测试，不能创建空页面伪造成功。

E. 按 P8 功能表逐项连通真实权限/供应商能力。先做博主主页采集与视频转录链的 Provider 对账、数据授权和用户验收，再扩 73 组、3,920 项。不允许把 catalogued 计为 validated。

最终分开统计 Catalogued / L2 Designed / Implemented / Tested / Integrated / Validated / Production Ready；只有最终两个项目的真实业务验收和安全门禁全部通过，才报告“完成”。
