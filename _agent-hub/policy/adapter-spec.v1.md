# ModelPolicyAdapter 规范 v1

> **SSOT**: `D:\AIOS\_agent-hub\policy\adapter-spec.v1.md`
> **依赖**: `D:\AIOS\_agent-hub\policy\model-policy.v1.yaml`（v1 · sha256 由 T5 验证）
> **作者**: Codex (aios-sovereignty-v engineering thread, W8 派单)
> **落盘**: 2026-10-09T00:0xZ

---

## 目的

为每个受控执行环境（Codex / Claude Code / OpenClaw / Hermes）定义**统一的策略校验接口**，
使所有模型调用在执行前经过一次**确定性**校验，拒绝不合规请求 **而不 fallback**。

本规范与 `adapter-contract.md`（v0.1 · 4 接口）的关系：
- `adapter-contract.md` = 顶层契约文档（read_effective_policy / intercept_request / audit_call / reconcile）
- **`adapter-spec.v1.md` = 每个 runtime 的本地 Adapter 入口规范**（聚焦单一 `validate()` 接口）
- Adapter 必须实现 `adapter-contract.md` 的 4 接口 + 本规范的 `validate()` 入口

---

## 统一接口

```python
from typing import Tuple

def validate(model: str, provider: str, *, request_id: str) -> Tuple[bool, str]:
    """校验一次模型调用请求是否符合当前策略。

    参数:
        model:       请求的模型 ID（必须存在于 policy.allowed_providers[*].models）
        provider:    请求的 provider（必须存在于 policy.allowed_providers）
        request_id:  调用方生成的请求 ID（用于审计追踪；keyword-only 强制必填）

    返回:
        (True, "ok")                  — 请求放行
        (False, "<reason>")           — 请求拒绝；reason 解释原因（≤ 200 字符）

    红线契约（违反任一 → Adapter 不合规，禁止使用）:
        - NO_FABRICATE_MODEL_ID       — model id 必须从 policy 文件读取；禁止硬编码/编造
        - UNIFIED_INTERFACE_REQUIRED  — 签名必须是 (model, provider, *, request_id) -> Tuple[bool, str]
        - NO_AUTO_FALLBACK_IN_ADAPTER — 拒绝时绝不自动切换 provider/model/路由
    """
```

---

## 调用方契约（Caller Contract）

### 调用时机
- **必须**: 每次模型调用发起前**同步**调用 `validate()`
- **必须**: 调用通过后**才**允许发起 HTTP 请求 / CLI 启动 / session fork
- **禁止**: 跳过 validate 直接发请求（即"零成本但合规违规"路径）

### 调用参数生成
| 参数 | 来源 | 红线 |
|---|---|---|
| `model` | 调用方内部配置或注册表读取 | 禁止从 env var / 启动参数 / 外部注入未经验证的值 |
| `provider` | 同上 | 不允许在调用前已"试过"其他 provider 后再调用 validate 伪装 |
| `request_id` | 调用方生成（UUID4 或 trace_id） | keyword-only；调用方必须生成并保留用于审计关联 |

### 拒绝处理
- `validate()` 返回 `(False, reason)` 时：
  1. 调用方必须**终止请求**（不发包 / 不启动 CLI / 不恢复 session）
  2. 调用方必须**记录**拒绝事件（含 reason + request_id）到本地 reject log
  3. 调用方**不得**重试（除非用户后续更新 policy 后显式触发）
- `validate()` 自身失败（policy 文件缺失 / 解析异常 / sha256 不匹配）：
  - 返回 `(False, "policy_unavailable")`
  - 调用方进入 `unavailable_handling` 流程（queue_with_backoff + report_to_audit_log + do_non_model_work）

---

## Adapter 实现要求

### 读取 Policy
```python
import yaml, hashlib
POLICY_PATH = r"D:\AIOS\_agent-hub\policy\model-policy.v1.yaml"
SHA_PATH    = r"D:\AIOS\_agent-hub\policy\model-policy.v1.sha256"

def _load_policy():
    raw = open(POLICY_PATH, "rb").read()
    expected = open(SHA_PATH).read().strip().split()[0].upper()
    actual = hashlib.sha256(raw).hexdigest().upper()
    if actual != expected:
        raise RuntimeError(f"policy sha256 mismatch: {actual} vs {expected}")
    return yaml.safe_load(raw)
```

### validate 校验顺序
按以下顺序短路返回（命中即返回）：

1. **provider 白名单**: `provider ∈ policy.model_policy.allowed_providers[*].id`
   - 失败 → `(False, "provider_not_allowed:{provider}")`
2. **provider 启用**: `allowed_providers[provider].enabled == True`
   - 失败 → `(False, "provider_disabled:{provider}")`
3. **model 白名单**: `model ∈ allowed_providers[provider].models[*].id`
   - 失败 → `(False, "model_not_allowed:{model}")`
4. **model 启用**: `model.enabled == True`
   - 失败 → `(False, "model_disabled:{model}")`
5. **未在 prohibited 列表**: 不命中 `prohibited_runtime_routes`
   - 失败 → `(False, "route_prohibited:{route}")`
6. **全部通过** → `(True, "ok")`

### 审计日志
- 每次 `validate()` 调用都写一行到 `D:\AIOS\_agent-hub\audit\adapter-validations.log`
- 格式（JSONL）:
  ```json
  {"ts":"2026-10-09T00:00:00+08:00","runtime":"<host>","model":"...","provider":"...","request_id":"...","allowed":true,"reason":"ok"}
  ```
- 拒绝时 `allowed=false, reason=<reason>`
- Adapter 异常（policy 不可读 / sha256 不匹配）也必须写日志（`allowed=false, reason="policy_unavailable"`）

---

## 红线（写进 SSOT · 永久态）

| ID | 红线 | 验证方式 |
|---|---|---|
| `NO_FABRICATE_MODEL_ID` | Adapter 不得在代码中硬编码任何 model id；必须从 policy 文件读取 | grep `Adapter 实现` 内是否有 `model_id = "..."` 字面量；静态扫描 |
| `UNIFIED_INTERFACE_REQUIRED` | 所有 Adapter 必须用同一签名 `(model, provider, *, request_id) -> Tuple[bool, str]` | regression-tests 强制 import + signature check |
| `NO_AUTO_FALLBACK_IN_ADAPTER` | Adapter 拒绝时不得重试 / 切换 provider / 切换 model | 拒绝路径下 grep 是否出现 retry/swap/fallback 关键字 |

任一红线被违反 → 该 runtime 不被允许承载 sovereignty-v 验收（即使单测全过）。

---

## 与 model-policy.v1.yaml 的绑定

| 字段 | Adapter 行为 |
|---|---|
| `default_provider` / `default_model` | validate 的隐含默认值；调用方未传时 Adapter 仍需校验两者均 allowed |
| `allowed_providers[*].models[*].evidence` | Adapter 不读 evidence；只读 `id` + `enabled` |
| `allowed_fallbacks` | **为空**；Adapter 必须遵守（NO_AUTO_FALLBACK_IN_ADAPTER 的 YAML 锚点） |
| `prohibited_runtime_routes` | validate 校验时硬匹配；命中即拒绝 |
| `unavailable_handling` | 仅在 Adapter 自身 fail（policy 不可读）时生效；调用方流程不在 Adapter 内 |

---

## 验收清单（W8 done 判定）

- [x] `D:\AIOS\_agent-hub\policy\adapter-spec.v1.md` 落盘（本文件）
- [ ] 4 个 runtime Adapter（Codex / Claude Code / OpenClaw / Hermes）按本规范实现 `validate()` 入口
  - 状态：等待 T7/T8 continuation 派单产出
- [ ] regression_tests.py 含本规范的 5 项契约测试（见下一节）
- [ ] sha256 验签生效（policy 文件被改 → Adapter 启动拒绝）
- [ ] 审计日志写入实测（每 validate 一行 JSONL）

---

## 契约测试项（regression_tests.py §adapter-spec.v1）

| # | 名称 | 断言 |
|---|---|---|
| 1 | `test_validate_signature_unified` | 4 个 runtime Adapter 的 `validate` 必须是 `(model, provider, *, request_id) -> Tuple[bool, str]` |
| 2 | `test_no_fabricate_model_id` | grep Adapter 实现，禁出现字面量 model id（除注释/字符串测试外） |
| 3 | `test_no_auto_fallback_in_adapter` | 拒绝路径源码中禁出现 `retry/swap/fallback` 调用 |
| 4 | `test_validate_policy_sha256_enforced` | 篡改 policy → Adapter 启动报 `policy_unavailable` |
| 5 | `test_validate_audit_log_written` | 每次调用 → `adapter-validations.log` 增 1 行 JSONL |

---

## 不在范围

- 真实 4 个 runtime Adapter 的实现代码（由 T7/T8 continuation envelope 产出）
- policy 文件本身的生成 / 签名脚本（model-policy.v1.yaml 已落盘，T5 验签已规划）
- Reconciler 实现（见 `reconciler-spec.md`）
- Adapter 性能基准 / 压测（待 W11+）

---

## 引用

- 上层契约: `policy/adapter-contract.md`（4 接口顶层）
- 策略 SSOT: `policy/model-policy.v1.yaml`
- 校验脚本: `policy/model-policy.v1.sha256`
- Reconciler: `policy/reconciler-spec.md`
- 漂移事件: `policy/drift-event.schema.json`
- 工程线程: `01a11c33-c813-7752-9e53-b7c332d00445`（W8 派单）
- 上游线程: `01a11c23-ab7f-7253-9059-7aa7fc204c02`（continuation）

---

_本规范为 sovereignty-v 阶段 W8 单点产出；任何 Adapter 偏离红线 → 验收不通过。_