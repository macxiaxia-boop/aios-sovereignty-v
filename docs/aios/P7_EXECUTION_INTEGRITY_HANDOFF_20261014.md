# AIOS P7｜细胞级执行权、外部副作用账本与交接证据

> 2026-10-14；延续 P0–P6。不是新系统，不是第二套调度器，不代表 Windows 或生产已验收。

## 0. 实际修改入口

**当前草稿 PR**：https://github.com/macxiaxia-boop/aios-sovereignty-v/pull/3

现有代码修改：`src/aios_kernel/workflows/persistence.py`、`engine.py`、`step.py`、`workflow.py`；强制测试放在 `tests/integration/test_p7_*.py`。CI 已显式纳入三版本测试。

**原始数字劳动力全量台账不重复生成**：327 数字员工、53 专家团、10 部门、50 岗位、3190 技能目录、15 套件、100 插件、133 MCP、42 RPA（38 具体描述 + 4 缺失）共 3920 个目录对象。目录对象不能冒充已经实现的功能。

## 1. 已编码的机制（待以最新提交 CI 审批）

### 1.1 执行权的骨骼：workflow_leases

字段：`run_id`（唯一键），`owner_id`（单次执行 UUID），`fencing_token`（获取执行权时单调递增），`expires_at`。

获取方式：初始化租约行后按 `expires_at <= now` 的条件原子 UPDATE，带 fencing token 自增；活跃 owner 不会收到第二张执行许可证；失效后接管产生更大的 fencing token。

心跳：运行中每 TTL/3 续租。检查点/运行完成前，必须在**同一数据库事务**中使用 owner/token/到期条件验证执行权。被接管的旧 Worker 不得再写可信检查点。

局限：失去租约的旧 Worker 可能已完成外部平台动作，租约无法回滚远端副作用。必须联用平台幂等键与核验机制；不得宣称 end-to-end exactly-once。TTL 当前设 120 秒，仍需实际资源耗时和故障注入测试。

### 1.2 神经/经络：稳定操作身份

每次 `ActivityContext.metadata` 携带：
- `fencing_token`：区分不同执行租约；
- `idempotency_key = SHA256(run_id + ":" + step_id)`：同一动作跨重试保持相同键；
- 原始 `workflow_input` 和依赖步骤 `deps` 保持透传。

**重要**：这只给出工具接口需要的身份材料。平台适配器必须确实传递 `idempotency_key` 并支持查询/去重才有效。

### 1.3 外部操作的血液/免疫：workflow_effects

字段：`effect_key` 唯一、`run_id`、`step_id`、`request_hash`、`status`、`receipt_json`、`reconciliation_evidence`。

仅当步骤显式设置 `WorkflowStep(external_effect=True)`，执行器才启用此策略；已有纯计算步骤不受影响。

状态机：

- PREPARED → SENT：先持久记录准备的操作，再执行外部调用。
- SENT → UNCERTAIN：调用超时、异常、返回失败或缺少可定位的远端资源回执。
- SENT → UNVERIFIED：拿到了包含 provider / resource_id 的回执，但**尚无独立查询证据**。
- SENT/UNCERTAIN/UNVERIFIED → CONFIRMED：由具备权限的核验程序取得远端真实资源证据，调用对账接口。
- CONFIRMED → 工作流恢复：从已记录的输出恢复，不重放已经发生的外部动作。

如果操作为 SENT、UNCERTAIN 或 UNVERIFIED，工作流必须标记 `blocked`，不允许凭通用重试策略再次发布。含回执字段不是经过核验的充分条件。

### 1.4 用户取消期间在途执行

取消发生在最后一个 Activity 运行中时，最终完成路径不得把 `cancelled` 覆盖成 `completed`。取消前可能已经出现的远端副作用仍需额外核对，不能只看任务状态。

## 2. 实际失败场景（必须独立重复）

| 编号 | 故障注入 | 期望结果 |
|---|---|---|
| P7-01 | 两个 Worker 竞争同 run_id | 只有一个获取租约 |
| P7-02 | 旧 owner 已过期，后任接管 | fencing token 增加；旧 owner 无法续租和写结果 |
| P7-03 | 慢步骤运行时另一个 resume | 后者被拒绝，外部动作不会由它重复运行 |
| P7-04 | 业务输入与依赖输出相同但 worker 重试 | idempotency_key 稳定 |
| P7-05 | 最后一项进行中用户取消 | 终态不能回写成 completed |
| P7-06 | 外部 API 发出后超时 | status=blocked，journal=uncertain，禁止盲重试 |
| P7-07 | 平台只返回文字 success，无 resource_id | 仍 blocked |
| P7-08 | 平台返回 resource_id，但未独立核验 | journal=unverified，仍 blocked |
| P7-09 | 正式对账证据存在，核验后 resume | 不重新调用外部平台，结果从 journal 读取 |
| P7-10 | 对账证据为空、回执缺少 ID | 必须拒绝确认 |

基础命令：`python -m pytest tests/integration/test_p5_workflow_integrity.py tests/integration/test_p6_atomic_claim.py tests/integration/test_p7_workflow_leases.py tests/integration/test_p7_effect_context.py tests/integration/test_p7_external_effects.py -q`

## 3. 未完成红线（不能用绿色 CI 冒充）

| 阻断 | 具体位置 / 证据要求 | 下一施工方向 |
|---|---|---|
| 不具备完整持久任务队列 | `scheduler.py` 仍基于 `asyncio.Queue` | 将 Gateway 提交、持久任务、认领、Worker 分派、ACK、恢复接成单链 |
| 尚无真实平台对账 | `confirm_external_effect` 接受调用方传入的证据字符串，**不自行检查平台** | 建立有授权、只读的 Provider Verifier，记录来源账号、resource_id、查询时间、结果哈希与审批身份 |
| 多进程 crash-kill 尚未验证 | CI 以 SQLite 测试为主 | PostgreSQL 双进程争抢、kill -9、TTL 过期、接管与检查点物证 |
| 租约未连接实际工具 | 当前 ActivityContext 提供 fencing token，但远端不能强制验证 | 对相关 Provider / DB 写 API 实施 fencing 检查和幂等键传播 |
| 未连接用户 Windows AIOS | 无本地 Agent 执行/文件/服务授权通路 | 本机 Codex 只读扫描、基线匹配、隔离运行、故障注入、真实验收 |
| CloudTech 前端未构建通过 | `web/vite-spa/src/App.tsx` 引用缺失 `./pages/lynxce/index` | 搜索现有分支、真实页面资产来源，不创建空白页伪造修复 |
| CloudTech 发布仍未通过独立核验 | PR #1 为 fail-closed 管线改造 | 先选一个已授权平台，用 mock → 沙箱 → 实际受控资源核验，禁止未经批准发帖 |
| 3920 项仍仅目录覆盖 | 业务 Agent 与 Skill 数量不等于 L2-L5 验证数量 | 从通用原子能力和真实工作链逐项深剖并绑定证据 |

## 4. 交给本机 Codex 的强制工作顺序

1. 不新建仓库，不直接改 main/master。检出现有两个草稿 PR，对照最新 SHA 和历史 baseline。
2. 先跑新增全部 P5–P7 回归测试；若失败，记日志和复现命令，按失败先行原则修到绿。不得仅靠忽略、删除测试取得绿灯。
3. 对 P7 新增数据库表写 **Alembic 迁移**：兼容已存在的生产数据库与备份回滚，不能只依赖 `create_all` 作为生产升级机制。
4. PostgreSQL 真实环境双进程竞争、租约过期、断网、进程被杀和恢复、长时间外部调用、恢复请求哈希不一致全部验收。
5. 实现真实 Provider 的回执验证接口，必须隔离租户/账户，读取官方允许访问的资源；尚无核验能力时外部步骤保持 blocked。
6. 将 `Gateway → Scheduler → WorkflowEngine → Worker → Verifier` 接成持久状态路径。每个链路记录 task_id/run_id/effect_key/trace_id/artifact/evidence，不容许只返回“success”。
7. 让 AGT-208 数字项目经理在现有 CloudTech 执行一次有限范围的假成功修复；产物为 PR、CI、测试、独立审查报告，而不是创建一个新的“项目经理 Agent”外壳。
8. 扩展下一批工作能力时，从原始 3920 台账中按依赖和业务功能选择对象，逐项递交 L2 内部结构、L3 代码测试、L4 真实工作证据。禁止按条目数批量打勾。

## 5. 严格完成状态

- **Source Catalogued**：原始目录已清点；不能冒充机制理解。
- **Designed L2**：有输入输出、数据契约、状态转移、依赖和失败路径。
- **Implemented**：在真实仓库修改代码。
- **Tested**：仓库 CI 显式执行相关测试且通过。
- **Integrated**：真实调用链打通且产生可核验工件。
- **Validated**：独立核验业务结果。
- **Production Ready**：安全、成本、租户隔离、恢复、实际环境和运维门禁全部通过。

PR 保持 Draft；不自动合并、部署、付费、发布或扩权限。完成门槛由证据决定，不由 ZIP、字数、Agent 数量决定。
