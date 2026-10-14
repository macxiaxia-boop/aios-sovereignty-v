# P9：AIOS 调用既有 CloudTech V4 的真实源码级闭环

> 这不是另建 CloudTech 或 AIOS，也不是“3,920 项功能已完工”。两份现有草稿 PR 是唯一代码来源：
> - AIOS https://github.com/macxiaxia-boop/aios-sovereignty-v/pull/3
> - CloudTech https://github.com/macxiaxia-boop/cloudtech-spa-v2/pull/1

## A. 已编码的串联链条

现有 `aios_kernel.gateway.http` 接收显式 Worker 绑定任务 → 现有 `AIOSScheduler` 依据 `worker="cloudtech-v4-adapter"` 路由 → `CloudTechV4Adapter.execute` → CloudTech V4 `GET /v4/workpaths/{path_id}/preflight` → `POST /v4/workpaths/runs` → `POST /v4/workpaths/runs/{run_id}/execute-local` → AIOS `ArtifactType.JSON` → Scheduler 保留 Artifact → 授权 `GET /tasks/{run_id}/result`。

仅允许 `action=preflight` 或 `action=create_and_execute_local`；其他动作禁止由 Gateway 传入。受限本地执行目前仅运行现有 V4 的 `url.normalize` 等源码证实的纯本地节点，**碰到第一个 Mock/未绑定 Provider 立即返回 PARTIAL/BLOCKED，不外发，不扣费**。

产物会标注 `business_validated:false`，HTTP Gateway 的 `completed` 只是 Worker 返回，不是内容生产或发布成功。不能将此阶段标为 Production Ready。

## B. Windows 双项目本机联调（仅回环地址）

以下环境变量用于隔离开发调试，不是对外上线说明。不要将 GitHub 草稿 PR 自动合并到主分支；先在本机检出并验证。

PowerShell 窗口 CloudTech：

```powershell
cd <CloudTech既有仓库目录>
$env:V4_ENV = "development"
python -m uvicorn api.v4.asgi:app --host 127.0.0.1 --port 5089
```

另一个 PowerShell 窗口 AIOS：

```powershell
cd <AIOS既有仓库目录>
$env:CLOUDTECH_V4_BASE_URL = "http://127.0.0.1:5089"
$env:CLOUDTECH_V4_GATEWAY_ENABLED = "1"
$env:AIOS_KERNEL_AUTH_REQUIRED = "1"
# JWT 密钥请由本机安全配置注入 32+ 字节；不要写入仓库或日志
# 由已有签发服务发一个具有 sub 和 tenant_id 的短期 Bearer JWT
python -m uvicorn aios_kernel.gateway.serve:app --host 127.0.0.1 --port 5090
```

**仅供隔离本机联调**：如果没有现成的 JWT 签发流程，请用系统既有 `sign_jwt` 生成本地测试身份；严禁将关鉴权的开发模式暴露在公网。CloudTech V4 目前仍是内存态开发服务，不可用此结果代替生产租户隔离。

### 本机受限任务示例（需传 AIOS 签发的 JWT）

```json
{
  "goal_id": "local-probe-001",
  "title": "CloudTech 博主主页路径实际本地能力核验",
  "priority": "P2",
  "worker": "cloudtech-v4-adapter",
  "input_payload": {
    "action": "create_and_execute_local",
    "tenant_id": "sandbox-tenant",
    "path_id": "WP-BLOGGER-RESEARCH",
    "input_bindings": {
      "homepage_url": "https://example.com/creator?cursor=1",
      "target_industry": "装修"
    }
  }
}
```

先发 `POST http://127.0.0.1:5090/tasks`（Authorization: Bearer JWT）获得 `run_id`；再查询 `GET /tasks/{run_id}` 与 `GET /tasks/{run_id}/result`（相同 JWT，JWT tenant_id 必须匹配）。理想状态：AIOS worker 已执行并返回可核查 JSON；内部 `local_execution` 只有 `url_normalize` 节点完成，随后在 `platform.permission_check` 停止，`business_validated=false`。绝对不要预期外部作品采集、付费生图或对外发帖在这一阶段成功。

## C. 依赖与证明义务

- CloudTech 已有六条 `WP-*` 路径与 50 个源码定义节点；P9 在 V4 上做静态完整性和实际零副作用节点执行，没有新建第二套业务系统。
- CloudTech V4 标为 `MOCK_ONLY`、`ADAPTER_UNMAPPED` 的节点不得执行或算完成；所有真实 Provider 必须走预算、账号授权、外部操作幂等/对账。
- AIOS `Gateway → Scheduler → Worker` 这条路径现在有代码、隔离测试；`Scheduler` 任务队列仍主要是内存 `asyncio.Queue`，不能声称具备重启自动续跑。
- AIOS P7 `WorkflowEngine` 的租约、fencing、外部副作用 journal **尚未自动覆盖 Scheduler 上的 CloudTech 任务**；跨两条引擎的真正 Durable Queue 串联仍需专项实现。
- CloudTech 前端 `App.tsx` 的 `pages/lynxce/index`（包含多页面）源文件在当前仓库和现有分支均未找到，必须按原有设计资产修复，不能添加空白 UI 虚报已完成。
- Windows 本机实际部署/真实 PostgreSQL 并发恢复/有权 Provider 远端资源核验仍未执行，状态只能是 PENDING/BLOCKED，不可填写 Validated 或 Production Ready。

## D. 每个任务的完整状态区分

1. `Catalogued`：3,920 目录对象与 73 组已登记，不等于 3,920 功能可运行。
2. `Designed`：30 条候选业务路线和 228 节点为研究视图；只有六条 V4 属于既有源码路径。
3. `Implemented`：以真实 PR 中源代码 diff 为准。
4. `Tested`：GitHub Actions HEAD 明确包含专项测试且通过。
5. `Integrated`：同一套运行环境里真正通过 Gateway→CloudTech 两进程调用并验证 Artifact。
6. `Validated`：外部平台、业务产物和用户验收条件由独立 Verifier 核验。
7. `Production Ready`：需完成多租户授权、持久任务队列、故障恢复、成本、审计和真实部署检查。

禁止自动合并/部署/发帖/付款/删库/提权。本次不创建新仓库、不复制数字员工空壳。
