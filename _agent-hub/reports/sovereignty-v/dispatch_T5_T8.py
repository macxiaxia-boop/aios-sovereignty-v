import sys, os, json, hashlib
sys.path.insert(0, r'D:\AIOS\_agent-hub\v2')
from src.envelope import build_envelope, envelope_to_json

ENGINEERING_TID = '01a11c33-c813-7752-9e53-b7c332d00445'
PARENT_TID      = '01a11c23-ab7f-7253-9059-7aa7fc204c02'
SUPER_TID       = '01a11c30-6f6c-76c0-8c60-a55f3a43ff63'
AUTHORIZER      = 'user-2026-10-08T23:55:你就开始'
POLICY_DIR      = r'D:\AIOS\_agent-hub\policy'
RECON_DIR       = r'D:\AIOS\_agent-hub\policy\reconciler'
REG_DIR         = r'D:\AIOS\_agent-hub\policy\regression-tests'
INBOX           = r'D:\AIOS\_agent-hub\v2\messages\inbox'

# Ensure policy dirs exist
for d in [POLICY_DIR, RECON_DIR, REG_DIR]:
    os.makedirs(d, exist_ok=True)

# ----- W7 ModelPolicy v1 YAML (T5) -----
W7_CONTENT = """# ModelPolicy v1 — single source of truth
# policy_id: model-policy
# policy_version: v1
# policy_owner: codex-supervisor
# generated_by: codex 01a11c30
# authorizer: user-2026-10-08T23:55 ("你就开始")
# generator: claude-code via sovereignty-v:T5 envelope
# status: pending-model-id-authorization

policy_id: model-policy
policy_version: "1.0.0"
policy_owner: codex-supervisor
allowed_providers:
  - MiniMax
# allowed_models: 留空 — 等用户明文授权 MiniMax model id 清单后由 Codex 补充
allowed_models: []
default_provider: MiniMax
# default_model: 同上，留空
default_model: null
allowed_fallbacks: []   # 仅 MiniMax 内部已授权选项；当前为空
prohibited_runtime_routes:
  - openai
  - anthropic
  - google
  - custom_other
last_modified: __FILL_AT_WRITE__
approval_evidence: AGENTS.md chapter 1 + parent_thread msg_<TODO>
applied_workers:
  - codex
  - claude-code
  - openclaw
  - hermes
  - workbuddy
verification_status: pending

# 强制约束
hard_constraints:
  - id: C1
    rule: "不得自动调用历史供应商"
  - id: C2
    rule: "不允许跨供应商自动 fallback"
  - id: C3
    rule: "不允许历史会话将旧模型重新设为当前模型"
  - id: C4
    rule: "不允许后台任务绕开统一策略"
  - id: C5
    rule: "不允许配置恢复将旧模型重新启用"
  - id: C6
    rule: "MiniMax 不可用时排队/退避/报告，不擅自换供应商"
  - id: C7
    rule: "AIOS 升级不得擅自修改本策略"
  - id: C8
    rule: "更换模型供应商需用户明确批准"
  - id: C9
    rule: "执行后真实模型来源必须可审计"
  - id: C10
    rule: "allowed_models 必须由用户授权 id 列表填入，禁止自行编造"
"""

# ----- W8 ModelPolicyAdapter 规范 (T6) -----
W8_CONTENT = """# ModelPolicyAdapter 规范 v1

## 目的
为每个受控执行环境（Codex / Claude Code / OpenClaw / Hermes）定义统一的策略校验接口，
使所有模型调用在执行前经过一次确定性校验，拒绝不合规请求而不 fallback。

## 统一接口

```python
from typing import Tuple

def validate(model: str, provider: str, *, request_id: str) -> Tuple[bool, str]:
    \"\"\"Validate a model call against ModelPolicy v1.

    Returns:
        (ok, reason)
        - (True, "OK") when (provider, model) is in allowed_*.
        - (False, "PROVIDER_NOT_ALLOWED") when provider not in allowed_providers.
        - (False, "MODEL_NOT_ALLOWED") when model not in allowed_models.
        - (False, "MINIMAX_UNAVAILABLE") when MiniMax temporarily unreachable
          (note: this is NOT a policy violation; caller should queue/backoff/report).
        - (False, "ROUTE_PROHIBITED") when (provider, model) hits prohibited_runtime_routes.

    Hard rules:
      - Never auto-fallback to a different provider.
      - Never retry with a different model.
      - Always log rejection with request_id.
    \"\"\"
    ...
```

## 各端 Adapter 映射

| Adapter | 实现位置 | 配置读取 |
|---|---|---|
| Codex Adapter | `kernel/src/aios_kernel/governance/codex_policy_adapter.py` | `D:\\AIOS\\_agent-hub\\policy\\model-policy.v1.yaml` |
| Claude Code Adapter | `kernel/src/aios_kernel/governance/claude_policy_adapter.py` | 同上 |
| OpenClaw Adapter | `kernel/src/aios_kernel/governance/openclaw_policy_adapter.py` | 同上 |
| Hermes Adapter | `kernel/src/aios_kernel/governance/hermes_policy_adapter.py` | 同上 |

## 钩子点
- Codex: 模型调用前 (`codex_kernel.invoke_model` hook)
- Claude Code: 启动 + 每次 `--model` 参数解析
- OpenClaw: agents/cron/heartbeat 三处 payload 解析
- Hermes: Skill 运行时 + 会话恢复钩子

## 审计
每次 validate() 调用写 `audit/model-policy-audit.jsonl`，含：
- timestamp
- request_id
- caller (which adapter)
- (model, provider) requested
- decision (allow/deny + reason)
- policy_id + policy_version
"""

# ----- W9 Reconciler 部署 (T7) -----
W9_DEPLOY_SCRIPT = """@echo off
REM Model Policy Reconciler — Task Scheduler registration
REM mode: persistent (default A); override to on-demand by setting MODE=on_demand

setlocal
set POLICY_PATH=D:\\AIOS\\_agent-hub\\policy\\model-policy.v1.yaml
set RECON_DIR=D:\\AIOS\\_agent-hub\\policy\\reconciler
set TASK_NAME=AIOS_ModelPolicy_Reconciler

REM Ensure single instance
tasklist | findstr /I "ModelPolicyReconciler.exe" >nul
if %ERRORLEVEL%==0 (
  echo Reconciler already running. Skipping start.
  exit /b 0
)

REM Register Task Scheduler (runs every 5 min, persistent)
schtasks /Create /TN "%TASK_NAME%" /TR "python %RECON_DIR%\\reconciler.py --policy %POLICY_PATH%" /SC MINUTE /MO 5 /F
if errorlevel 1 (
  echo Failed to register task. Falling back to on-demand.
  start "" python "%RECON_DIR%\\reconciler.py" --policy "%POLICY_PATH%"
) else (
  echo Reconciler registered as %TASK_NAME% (5-minute interval).
)
endlocal
"""

W9_RECONCILER_PY = """#!/usr/bin/env python3
# Model Policy Reconciler
# Scans running AIOS-related processes, checks actual loaded providers against policy,
# alerts on non-compliance, NEVER auto-modifies.
import argparse, os, sys, json, hashlib, time
from pathlib import Path

POLICY_PATH_DEFAULT = r"D:\\AIOS\\_agent-hub\\policy\\model-policy.v1.yaml"
ALERT_PATH = r"D:\\AIOS\\_agent-hub\\policy\\reconciler\\alerts.jsonl"

def load_policy(path: str) -> dict:
    import yaml
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def scan_processes() -> list:
    # Read process list without modifying
    proc_data = []
    try:
        import subprocess
        out = subprocess.run(["wmic", "process", "get", "Name,ProcessId,CommandLine", "/FORMAT:CSV"],
                             capture_output=True, text=True, timeout=10)
        for line in out.stdout.splitlines()[1:]:
            parts = line.split(",")
            if len(parts) >= 3:
                proc_data.append({"name": parts[0], "pid": parts[1], "cmdline": parts[2]})
    except Exception as e:
        proc_data.append({"error": str(e)})
    return proc_data

def check_compliance(policy: dict, procs: list) -> list:
    violations = []
    allowed = set(policy.get("allowed_providers", []))
    prohibited = set(policy.get("prohibited_runtime_routes", []))
    targets = {"codex", "claude", "openclaw", "hermes"}
    for p in procs:
        name = (p.get("name") or "").lower()
        cmd = (p.get("cmdline") or "").lower()
        if not any(t in name for t in targets):
            continue
        for prov in prohibited:
            if prov in cmd:
                violations.append({"proc": p, "violation": f"prohibited_route:{prov}"})
        # Note: allowed_providers match requires deeper cmdline parsing
        # If provider NOT in allowed_providers AND NOT in prohibited_runtime_routes,
        # still flag as "unknown_provider".
        if not any(prov in cmd for prov in allowed):
            if not any(prov in cmd for prov in prohibited):
                # could be just a process not actually invoking model; skip
                pass
    return violations

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default=POLICY_PATH_DEFAULT)
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()
    policy = load_policy(args.policy)
    procs = scan_processes()
    violations = check_compliance(policy, procs)
    if violations:
        with open(ALERT_PATH, "a", encoding="utf-8") as f:
            for v in violations:
                f.write(json.dumps({"ts": time.time(), **v}) + "\\n")
        print(f"ALERT: {len(violations)} violations found. See {ALERT_PATH}")
    else:
        print(f"OK: {len(procs)} procs scanned, 0 violations.")

if __name__ == "__main__":
    main()
"""

# ----- W10 回归测试 1-18 (T8) -----
W10_TESTS = """# ModelPolicy v1 回归测试 1-18

每项测试必须可独立运行：python test_<NN>.py
所有测试通过 = T8 PASS。

## R 风险编号映射
R1 备份/快照被自动恢复              → test_01.py + test_02.py
R2 cc-switch 在不知情下回滚           → test_03.py + test_04.py
R3 Cron / heartbeat payload 携带覆盖 → test_07.py + test_08.py
R4 历史 session restore 重新激活      → test_09.py + test_10.py
R5 两个 Reconciler 互相覆盖           → test_11.py
R6 不可拦截的外部程序                  → test_12.py
R7 备份目录被自动扫描恢复              → test_13.py
R8 策略文件本身被改写                  → test_14.py + test_15.py
R9 MiniMax 临时不可用被误判            → test_16.py
R10 用户授权 model id 误填/虚构        → test_17.py + test_18.py

## 占位测试框架（Claude Code 落实）

```python
# test_01.py — R1.a: 备份恢复不会自动加载
def test_backup_not_autoreloaded():
    # 1. 在 sandbox 创建假 backup 目录 .aios-archive
    # 2. 触发 Reconciler
    # 3. 验证 backup 未被自动加载
    assert True  # Claude Code 实现
```

(repeat for test_02 through test_18)
"""

results = []

# T5 — W7 ModelPolicy YAML
payload_t5 = {
    'task_id': 'sovereignty-v:T5',
    'engineering_thread_id': ENGINEERING_TID,
    'parent_thread_id': PARENT_TID,
    'supervisor_thread_id': SUPER_TID,
    'phase': 'SOVEREIGNTY-V',
    'mode': 'WRITE_POLICY_YAML',
    'task_card': 'T5',
    'title': 'Generate ModelPolicy v1 YAML (sha256 + chmod 444)',
    'artifacts': ['W7'],
    'output_paths': {
        'W7_yaml': f'{POLICY_DIR}\\model-policy.v1.yaml',
        'W7_sha256': f'{POLICY_DIR}\\model-policy.v1.yaml.sha256',
        'T5_done': r'D:\AIOS\_agent-hub\reports\sovereignty-v\tasks\T5.done',
    },
    'policy_yaml_template': W7_CONTENT,
    'post_write_actions': [
        'Get-FileHash -Path model-policy.v1.yaml -Algorithm SHA256 | Out-File model-policy.v1.yaml.sha256',
        'icacls model-policy.v1.yaml /inheritance:r /grant:r "$env:USERNAME:(R)"  # disable inheritance, read-only for owner',
    ],
    'red_lines': [
        'NO_FABRICATE_MODEL_ID',
        'allowed_models_MUST_BE_EMPTY_ARRAY',
        'default_model_MUST_BE_NULL',
        'NO_WRITE_FALLBACK_TO_NON_MINIMAX',
    ],
    'pending_authorizations': [
        'allowed_models: 等用户明文给 MiniMax model id 清单后填',
        'last_modified: 写盘时由 Claude Code 填 ISO8601',
    ],
    'authorizer': AUTHORIZER,
    'expected_runtime_seconds': 60,
}
env5 = build_envelope(sender='codex', recipient='claudecode', message_type='task',
                     payload=payload_t5, artifact_refs=['W7'], ttl_ms=600000)
p5 = os.path.join(INBOX, f"{env5['id']}__codex__claudecode__task.json")
with open(p5,'w',encoding='utf-8') as f:
    f.write(envelope_to_json(env5))
results.append(('T5', p5, env5['id']))

# T6 — W8 Adapter spec
payload_t6 = {
    'task_id': 'sovereignty-v:T6',
    'engineering_thread_id': ENGINEERING_TID,
    'parent_thread_id': PARENT_TID,
    'supervisor_thread_id': SUPER_TID,
    'phase': 'SOVEREIGNTY-V',
    'mode': 'WRITE_ADAPTER_SPEC',
    'task_card': 'T6',
    'title': 'Generate ModelPolicyAdapter spec for Codex/CC/OpenClaw/Hermes',
    'artifacts': ['W8'],
    'output_paths': {
        'W8_spec': f'{POLICY_DIR}\\adapter-spec.v1.md',
        'T6_done': r'D:\AIOS\_agent-hub\reports\sovereignty-v\tasks\T6.done',
    },
    'spec_template': W8_CONTENT,
    'red_lines': [
        'NO_FABRICATE_MODEL_ID',
        'UNIFIED_INTERFACE_REQUIRED',
        'NO_AUTO_FALLBACK_IN_ADAPTER',
    ],
    'authorizer': AUTHORIZER,
    'expected_runtime_seconds': 60,
}
env6 = build_envelope(sender='codex', recipient='claudecode', message_type='task',
                     payload=payload_t6, artifact_refs=['W8'], ttl_ms=600000)
p6 = os.path.join(INBOX, f"{env6['id']}__codex__claudecode__task.json")
with open(p6,'w',encoding='utf-8') as f:
    f.write(envelope_to_json(env6))
results.append(('T6', p6, env6['id']))

# T7 — W9 Reconciler (mode = A = persistent Task Scheduler)
payload_t7 = {
    'task_id': 'sovereignty-v:T7',
    'engineering_thread_id': ENGINEERING_TID,
    'parent_thread_id': PARENT_TID,
    'supervisor_thread_id': SUPER_TID,
    'phase': 'SOVEREIGNTY-V',
    'mode': 'WRITE_DEPLOY_RECONCILER',
    'task_card': 'T7',
    'title': 'Deploy Reconciler — DEFAULT mode A (Task Scheduler persistent, 5-min interval)',
    'artifacts': ['W9'],
    'output_paths': {
        'W9_dir': RECON_DIR,
        'W9_reconciler_py': f'{RECON_DIR}\\reconciler.py',
        'W9_register_cmd': f'{RECON_DIR}\\register_reconciler.cmd',
        'T7_done': r'D:\AIOS\_agent-hub\reports\sovereignty-v\tasks\T7.done',
    },
    'reconciler_py_template': W9_RECONCILER_PY,
    'register_cmd_template': W9_DEPLOY_SCRIPT,
    'deployment_choice': 'A_persistent_task_scheduler',
    'fallback_if_schtasks_fails': 'B_on_demand_startup_hook',
    'red_lines': [
        'NO_AUTO_MODIFY_CONFIG',
        'SINGLE_INSTANCE_REQUIRED',
        'NO_LEADER_ELECTION_SKIP',
        'RECONCILER_NEVER_MODIFIES_POLICY_FILE',
    ],
    'authorizer': AUTHORIZER,
    'expected_runtime_seconds': 90,
}
env7 = build_envelope(sender='codex', recipient='claudecode', message_type='task',
                     payload=payload_t7, artifact_refs=['W9'], ttl_ms=600000)
p7 = os.path.join(INBOX, f"{env7['id']}__codex__claudecode__task.json")
with open(p7,'w',encoding='utf-8') as f:
    f.write(envelope_to_json(env7))
results.append(('T7', p7, env7['id']))

# T8 — W10 Regression tests 1-18
payload_t8 = {
    'task_id': 'sovereignty-v:T8',
    'engineering_thread_id': ENGINEERING_TID,
    'parent_thread_id': PARENT_TID,
    'supervisor_thread_id': SUPER_TID,
    'phase': 'SOVEREIGNTY-V',
    'mode': 'WRITE_REGRESSION_TESTS',
    'task_card': 'T8',
    'title': 'Regression tests 1-18 per risk R1-R10 mapping',
    'artifacts': ['W10'],
    'output_paths': {
        'W10_dir': REG_DIR,
        'W10_index': f'{REG_DIR}\\README.md',
        'T8_done': r'D:\AIOS\_agent-hub\reports\sovereignty-v\tasks\T8.done',
    },
    'tests_template': W10_TESTS,
    'risk_mapping': 'R1->test_01+02, R2->test_03+04, R3->test_07+08, R4->test_09+10, R5->test_11, R6->test_12, R7->test_13, R8->test_14+15, R9->test_16, R10->test_17+18',
    'red_lines': [
        'NO_FABRICATE_TEST_PASS_WITHOUT_RUNNING',
        'EACH_TEST_MUST_BE_INDEPENDENT_RUNNABLE',
    ],
    'authorizer': AUTHORIZER,
    'expected_runtime_seconds': 240,
}
env8 = build_envelope(sender='codex', recipient='claudecode', message_type='task',
                     payload=payload_t8, artifact_refs=['W10'], ttl_ms=600000)
p8 = os.path.join(INBOX, f"{env8['id']}__codex__claudecode__task.json")
with open(p8,'w',encoding='utf-8') as f:
    f.write(envelope_to_json(env8))
results.append(('T8', p8, env8['id']))

for r in results:
    print('DISPATCH', r[0], '->', r[1])
print('TOTAL_DISPATCHED', len(results))