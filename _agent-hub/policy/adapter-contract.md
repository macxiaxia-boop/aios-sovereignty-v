# ModelPolicy Adapter Contract v1

## 目的
让每个 runtime（Codex / ClaudeCode / OpenClaw / Hermes / cc-switch）按各自原生格式实现，但接口语义统一。

## 接口

### read_effective_policy() -> Policy
- 读取 D:\AIOS\_agent-hub\policy\model-policy.v1.yaml
- 校验 sha256 与 manifest 一致；不一致 → 安全失败（拒绝 + 告警）
- 缓存策略：进程启动时读一次 + Reconciler 推送时刷新

### intercept_request(model_id, provider_hint, route_hint) -> Decision
- 校验顺序：
  1. provider ∈ allowed_providers?
  2. model_id ∈ allowed_models[provider]?
  3. route_hint 出站域名 ∈ allowed_egress?
  4. 不在 prohibited_runtime_routes 列表?
- 返回: ALLOW | DENY(reason)
- DENY 时：
  - 写一条 DriftEvent / RejectEvent 到审计日志
  - 绝不自动 fallback
  - 若 unavailable_handling 触发 → 排队/退避/报告

### audit_call(model_id, provider, route, billing_ref, ts)
- 仅在请求成功后调用
- 字段最小集：model_id, provider, route_url, billing_ref, ts
- 写入 D:\AIOS\_agent-hub\audit\model-calls.log（append-only）

### reconcile(actual_state) -> [DriftEvent]
- 由 Reconciler 周期调用
- 详见 reconciler-spec.md

## 不变量
1. Adapter 不能写 Policy 文件
2. Adapter 不能修改审计日志历史记录
3. Adapter 必须对每次拒绝留痕
4. Adapter 不可用 ≠ 策略违规；二者必须区分
