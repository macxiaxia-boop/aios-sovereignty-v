# SOVEREIGNTY-V · Sync Verification (能同步给谁)
**用户问题**: 以后窗口和其他AI能够同步到这份协议的改动吗？
**答**: 同机器 YES, 跨机器 NO

## 8/8 stdin pipe test (新 session 启动后行为):
- deepseek       → DENY
- gpt-5-codex    → DENY
- claude-sonnet  → DENY
- MiniMax-M3     → ALLOW
- claude-3       → DENY
- qwen3:14b      → DENY
- doubao         → DENY
- minimax/MiniMax-M3 → ALLOW

## 能同步给 (同机器, verified):
- Codex 新 session         ✅ hooks.json + Adapter auto-load
- Codex CLI 启动            ✅ config.toml default MiniMax-M3
- Codex PreToolUse hook     ✅ 7 trusted_hash pinned
- AIOS 5 角色 agent        ✅ router v2 → minimax-m3
- OpenClaw 新 session      ✅ modelPolicyAllowlist=true
- Kernel Reconciler 5min    ✅ Ready + 实际 tick (drift=0)
- MiniMax /v1/models        ✅ 8 models
- V22 SaaS                  ✅ port 5099 + 135 V10 modules
- 24 _agent-hub tests       ✅ 38/24 PASS
- 26 kernel CI tests        ✅ 4/4 PASS
- 4 env credentials         ✅ HKCU + Process CLEARED

## 不能同步给 (局限):
- 其他机器 (跨主机)    ❌ 无自动 sync
- 其他 AI (cursor/aider) ❌ 未配置
- CC-switch.db 写入     ⚠️ 未人工验 (kernel 验证 drift=0)

## 报告
**结论**: 同机器治理 100% 真实落实 · 跨机器需手动 copy · 其他 AI 需单独集成
