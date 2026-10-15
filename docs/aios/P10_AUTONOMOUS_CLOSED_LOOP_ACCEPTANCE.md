# P10：一次性闭环验收，不允许用“待办汇报”替代完成

本交接与既有 AIOS PR #3、CloudTech PR #1 及原 3920 项/73 组功能目录完全延续，**不得重新建仓库、创建重复 Agent、复制通用模板**。

## A. 本批明确的完成分母（禁止编造全量 95%）

| 实际验收工作项 | 通过条件 | 此文档提交时状态 |
|---|---|---|
| 原有 AIOS Gateway / Scheduler 启动 | `uvicorn aios_kernel.gateway.serve:app` loopback 启动并可查 /health | 已有源码，待 Windows 运行 |
| CloudTech V4 原有路由启动 | `uvicorn api.v4.asgi:app` loopback 启动并列出原 6 条路径 | 已有源码，待 Windows 运行 |
| Gateway 强制 JWT 租户绑定 | 无 JWT、不同租户，POST /tasks 均拒绝 | 代码及 CI 用例 |
| CloudTechV4Adapter 调用链 | preflight→创建 run→安全本地节点→JSON artifact | 代码及隔离测试 |
| P10 SQLite 先提交再排队 | DB 持久记录存在后才返回 run_id | 已编码，CI 验证为准 |
| 双实例竞争 | 单一 run 只能一个 claim 与 fence | 已编码、专项测试 |
| 崩溃后分类恢复 | 只读预检重入队，未知效果 blocked_uncertain | 已编码、专项测试 |
| 产物重启后查询 | SQLite 中持久 Artifact 可以由 JWT 租户读取 | 已编码、专项测试 |
| 真实双进程 HTTP 贯通 | 启动两个真实本地服务，使用 HTTP 返回首节点工件 | 测试脚本已编写，尚未有真实运行证据 |
| 可执行内容业务结果 | 主页采集/真实 ASR/原创/发布等 Provider 经授权接入并有可信回执 | 未完成，不能拿本地 URL.normalize 冒充 |
| Windows/生产应用 | 本机服务、权限、配置、持久卷和恢复验收 | 未验证 |
| 全量 3920 项机制+实际工作 | 各 source_id 逐项有源码、反例、真实成果和复盘 | 未完成 |

**完成比率仅针对有明确测试的本批任务计算，不用 3920 项源目录冒充已实现，也不得用 CI 通过冒充本机已上线。**

## B. 双仓真实 HTTP 实验

在 Windows 本地两个克隆的独立 PR 分支运行：

CloudTech:
```powershell
cd <已有CloudTech仓库路径>
$env:V4_ENV="development"
python -m uvicorn api.v4.asgi:app --host 127.0.0.1 --port 5089
```

AIOS:
```powershell
cd <已有AIOS仓库路径>
$env:PYTHONPATH="src"
$env:CLOUDTECH_V4_BASE_URL="http://127.0.0.1:5089"
$env:CLOUDTECH_V4_GATEWAY_ENABLED="1"
$env:AIOS_SCHEDULER_SQLITE_PATH="<本机已批准的隔离工作目录>/p10-dispatch.sqlite3"
$env:AIOS_KERNEL_AUTH_REQUIRED="1"
$env:AIOS_KERNEL_RATELIMIT_ENABLED="0"
# 在本机安全密钥存储中生成 32+ 字节的临时 JWT 密钥，
# 并以 AIOS_KERNEL_JWT_SECRET 注入。不要写入 GitHub、日志或截图。
python -m uvicorn aios_kernel.gateway.serve:app --host 127.0.0.1 --port 5090
```

第三个窗口：
```powershell
cd <已有AIOS仓库路径>
$env:PYTHONPATH="src"
python tests/integration/p10_crossrepo_http_smoke.py
```

此脚本只允许 localhost/127.0.0.1；会检查：
- CloudTech 实际发现六条原路径，且没有虚报业务可执行；
- AIOS 真正拒绝无 JWT 以及错误租户；
- 经真实 HTTP 提交 CloudTech V4 任务；
- 工件中仅 `url_normalize` 实际成功，权限 Mock 节点停止；
- 额外检查 `charged_cents=0`、`external_calls=0`、`business_validated=false`；
- 错误租户读结果得到 404。
这里不涉及真实博主采集、不实际发帖，也不意味着已经生产上线。

## C. 运行故障与修复顺序

1. 如果服务启动失败，首先读取完整 traceback 和当前文件的 Git SHA。不得凭想象新增替代后端。
2. 如果 CI 报 Ruff、pytest、导入契约问题，修源码或测试中的真实问题，保留失败复现和下一轮通过记录。
3. 如果单次任务成功、重启后丢失，优先检查 `AIOS_SCHEDULER_SQLITE_PATH` 的持久卷、run 行、fence 和状态；不得将 `MemoryPersistence` 当成稳定任务队列的充分证明。
4. 如果远端请求发出而无可信回执，不能盲重试；一律按 P7 `UNCERTAIN/UNVERIFIED` 和 ProviderVerifier 规范处理。
5. 开启 CloudTech 真实生产模式之前，必须解决当前 V4 开发态 `tenant_id` 信任问题，并实现不同租户的真实授权与资源回执核对。

## D. 与全量数字劳动力的关联（不跑偏）

原 327 Agent、53 专家团、3190 Skills、133 MCP、42 RPA 等皆为来源名称和候选业务能力。应先把 **A 原子能力（任务权限、调用、记忆、恢复、数据、输出验证）** 在真实调用链打通，再从原有 V4 6 条路径逐项用真实 Adapter 替换 Mock；每个可交付业务流都形成 source_id→operation→code_SHA→test→output_ref→independent-verdict。不要继续生成无代码对应的 3900 份高相似报告。

## E. 不可违反的授权边界

两个 PR 均保留 Draft，不自动合并；Windows 本机服务启动和凭据设置必须在受控环境；不公开发布任何服务器端口，不付款、不发帖、不删除用户数据、不扩大权限。所有完成统计独立区分 Code Implemented / CI Tested / Integrated Real HTTP / Business Validated / Production Ready。

> 这是一份完整施工与验收清单，不是已经通过的运行证据。执行过程中减少中间汇报；在一个清楚的工程批次达成验收，或遭遇真实无法突破的授权阻断时集中汇报。
