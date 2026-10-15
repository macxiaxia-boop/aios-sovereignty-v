# P8｜让 AIOS 真正知道“每组功能怎么做”的接管协议

工程来源：用户提供 3,920 个原始目录对象、73 个组；包含 327 Agent、53 专家团、10 部门、50 岗位、3190 Skills、15 Kits、100 Plugins、133 MCP、42 RPA。**这些只是来源清点，不是 3,920 项代码实现**。4 个 RPA 原始明细缺失，标记 SOURCE_BLOCKED。

CloudTech 已有 `workflows/v4/paths.py`：`WP-BLOGGER-RESEARCH`、`WP-VIDEO-TRANSCRIBE`、`WP-ARTICLE-REWRITE`、`WP-RENOVATION-FULL`、`WP-GROWTH-VIDEO`、`WP-PRODUCT-MARKETING`，50 个源码定义节点；不重建六条，也不改原 ID。P8 另外设计了 30 条业务场景路径/228 个原子节点、198 条候选依赖，作为跨 Agent/Skill/MCP/RPA 的研究与实现视图；需映射到 V4 原有节点。

## 每个对象必须形成的卡片

`source_id`、`source_claims`、`business_trigger`、`input_schema`、`output_schema`、`atomic_actions[]`、`dependency_edges[]`、`worker_role`、`tool_binding`、`permission_scope`、`retry_class`、`state_transition`、`failure_matrix`、`test_evidence`、`artifact_ref`、`implementation_sha`、`independent_verification`。

所有 `tool_binding` 默认 UNMAPPED，直到在**真实代码仓库**中能查到对应函数、签名和可运行测试。来源只给名称时不得凭空生成竞争者内部代码实现。共享细胞复用现有基础组件，Agent/专家团只负责不同业务角色的编排与审核，禁止 327 个 Agent 各复制一份检索/存储/权限代码。

## 单 Run 的真实调用路径

`Gateway Goal Intake → Persisted Task Envelope → Authorized Scheduler Dispatch → Worker Binding → V4 WorkPathDefinition → Registered Operation Adapter → Typed Output/Artifact → Independent Reviewer or Provider Verifier → Durable Final Status`。

必须用同一组 `tenant_id, task_id, run_id, path_id, node_id, effect_key, trace_id` 贯通所有组件。任何独立系统产生“完成”而没有对应 run 与真实产物，不得写入全局成功记录。

P5–P7 本分支现有修复涉及 SQL 方言、run_id 去重、工作流业务输入、检查点、租约、fencing、外部副作用账本、BLOCKED 状态及 P7 迁移。上述只是工具链基础，不是完整业务已集成。旧 `AIOSScheduler` 仍使用内存队列，Gateway → WorkflowEngine 完整持久调度链需本机核实。

## 明确的业务拆解与优先级

**A 博主主页研究**：主页 URL → 平台权限 → 分页采集 → 去重 → 各视频转录和结构分析 → 原创脚本 → 人审 → 资产包。要拒绝 CloudTech `homepage_parser` 目前的 MOCK 目录，将真实 API 与 mock 标识区分。

**B 视频原文/仿写**：有权媒体 → 下载及哈希 → ASR、帧提取 → 转录时间戳 → 原创脚本 → QC → 草稿。CloudTech ASR 和原创脚本当前有 mock-only 情形，没有真实 provider 的不得计为完成。

**C 图文提取/二创**：URL 访问 → 结构化正文、配图与顺序 → 版权/授权 → 事实研究 → 新大纲 → 原创内容 → 人审。未知 `article.*` 操作不得使用 stub 伪装。

**D 全屋改图**：户型+风格+家具图片角色绑定 → 房间级硬约束 → 费用审批 → 真实生图 provider → 局部变化保真 → 画面验收 → 版本归档。

**E 装修图生15秒视频**：首尾帧 → 运动规划 → 分段生成 → FFmpeg → 视频时长与编码检查 → 审核 → 可交付文件。

**F 商品营销全套**：商品真实照片 → 卖点事实 → 场景/多渠道适配 → 配图/视频/配音 → 合规 → 草稿归档 → 受控发布（需单独授权）。

**G 数字项目经理**：业务需求 → 需求/验收拆解 → PR 实施工单 → Codex 仅修改既有仓库 → CI → reviewer → 最终工件反馈。必须让 AGT-208 产品经理真正交付一条 CloudTech 失败路径的修复 PR，而不是创建一个人设。

其余营销、CRM、财务、法务、知识、HR、电商、MCP和RPA组从共享能力出发，依原始来源逐项扩展；每个 ID 要与真实能力和证据关联，不要批量加载未审查插件。

## 状态与对账门禁

1. 每个普通节点：`PENDING → READY → RUNNING → COMPLETED|FAILED|BLOCKED`。
2. 需审批的节点：`WAITING_APPROVAL`，审批必须绑定操作身份和参数哈希。
3. 对外操作：`PREPARED → SENT → UNVERIFIED|UNCERTAIN → CONFIRMED`；UNKNOWN 不能自动重放；同一 run:node 使用稳定幂等键。
4. 进程崩溃、超时、旧 Worker 失去租约后，无证据不得把任务报为成功。已发到平台但回执未知，等待只读 Provider Verifier。
5. `mock, stub, simulated, empty artifacts, no registered tool, no authorized provider` 全部不得进入业务 Validated。
6. 任何涉及发帖、付款、删库、权限提升、部署的外部动作必须有人类审批；AIOS 不得借长期运行指令绕过授权。

## 施工和统计

首先检查当前 PR #3 与 CloudTech PR #1 的最新 HEAD，按 P8 外部 ZIP 中的候选路径数据库/73组明细读取 source IDs，找已存在的工作流、工具、adapter 和测试；先逐一真实核查 V4 50 个节点的内部组成，再逐组扩展。缺失工具录入 GAP。每轮记录 `cataloged / designed / implemented / tested / integrated / validated / production_ready` 分项数量。不可用目录项数、模板文件数或 ZIP 大小冒充验收数。

**缺口**：Windows 本机连接器、真实 PostgreSQL 双进程执行测试、平台真实授权与独立回执验真、CloudTech 前端缺失 `pages/lynxce/index` 的原始来源、尚缺的 OCR/LLM/meeting adapter 等。若只有临时 mock，请保持未验证。

相关 CloudTech 路径对照已写进 CloudTech PR #1：`docs/aios/P8_V4_WORKPATH_SOURCE_AND_CELL_GAPS.md`。P8 主包另有完整 SQLite、30 条路径 JSON、228 节点 DAG、3920 项逐条候选映射、5 条字段合同与 Codex 长指令。文档不是执行证据，必须让 Codex 从源码验证并落地。
