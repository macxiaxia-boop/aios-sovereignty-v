# SOP <id> · <name> · <type>

type 必填（决定本文件是否可被 runtime 执行）：
- [ ] doc        → 仅文档；不能被 runtime 加载
- [ ] semi-auto  → 需人工触发 + 脚本执行
- [ ] auto       → runtime 注册的入口任务

## 必填字段（auto 必填；semi-auto 推荐；doc 可空）
- sop_id
- sop_version
- entry_task_type
- runner
- target_runtime
- prerequisites
- required_tools
- required_credentials_ref
- input_contract
- output_contract
- failure_handling
- acceptance_test
- rollback_path
- last_verified_at
- owner

## 分类命令
- "我是 doc"   → 人工执行；不接受 runtime 调度
- "我是 semi-auto" → 由 SOP runner 包装；缺字段 → 拒绝执行
- "我是 auto"   → Reconciler 监控其依赖与执行环境
