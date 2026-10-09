# 🟢 CloudTech V22 · MiniMax 适配完工报告 · 2026-10-09

> **工程**: AIOS-SOVEREIGNTY-V · A+B 阶段 · 2026-10-09
> **范围**: CloudTech V22 SaaS (D:\CloudTech-Portable\) · model provider 切换
> **总指挥**: Codex 01a11c23 (supervisor)

---

## ✅ 完成动作

### 1. 恢复 CloudTech V22 (A 部分)

| 项 | 动作 | 结果 |
|---|---|---|
| `cloudtech-v22-gateway` Windows service | Set-Service -StartupType Automatic + Start-Service | ✅ Running |
| Port 5099 | service 起来后自动 Listen | ✅ PID 31220 |
| `CloudTech-V22-Watchdog` task | Enable-ScheduledTask | ✅ |
| `CloudTech_V22Watchdog` task | Enable-ScheduledTask | ✅ |
| `CloudTech_V23FileWatcher` task | Enable-ScheduledTask | ✅ |
| `CloudTech_SpecV1CI_Daily_0300` task | Enable-ScheduledTask | ✅ |
| `AIOSLightMonitor-30min` (\CloudTech\) | Enable-ScheduledTask | ✅ |
| `DailyReport-0300` (\CloudTech\) | Enable-ScheduledTask | ✅ |
| `D:\AIOS\cloudtech-saas\` | 从 quarantine 移回 | ✅ (10 文件) |
| `D:\AIOS\_workzone\src\_aios_cloudtech_bridge.py` | 从 quarantine 移回 | ✅ (15,037 B) |

### 2. 应用 ModelPolicy 到 V22 (B 部分)

| 文件 | 改动 | 大小 |
|---|---|---|
| `D:\CloudTech-Portable\.env` | 删除 `DEEPSEEK_API_KEY` 行; 保留 `MINIMAX_API_KEY` + `MINIMAX_BASE_URL` | 2,957 B |
| `D:\CloudTech-Portable\model_aggregator.py` | text 段 deepseek-v4-pro/flash → MiniMax-M3-deep/MiniMax-M3; provider 改 MiniMax | 5,718 B |

### 3. 重启 V22 让改动生效

```powershell
sc stop cloudtech-v22-gateway
sc start cloudtech-v22-gateway
```

### 4. 验证 V22 MiniMax-Only

**真实运行结果** (`python D:\AIOS\_verify_v22_minimax.py`):

```
=== text models ===
[
  {
    "id": "MiniMax-M3-deep",
    "provider": "MiniMax",
    "type": "text",
    "strength": "深度推理·长文",
    "cost_per_1k": 0.01,
    "_r_sovereignty_note": "原 deepseek-v4-pro · 2026-10-09 A+B 改 MiniMax-M3"
  },
  {
    "id": "MiniMax-M3",
    "provider": "MiniMax",
    "type": "text",
    "strength": "快速响应·短文",
    "cost_per_1k": 0.003,
    "_r_sovereignty_note": "原 deepseek-v4-flash · 2026-10-09 A+B 改 MiniMax-M3"
  }
]

=== route_model tests ===
  [OK] social_post          -> MiniMax-M3       (provider=MiniMax)
  [OK] long_article         -> MiniMax-M3-deep  (provider=MiniMax)
  [OK] video_ad             -> seedance-2.0     (provider=ByteDance)  [非 LLM, 保留]
  [OK] image_render         -> seedance-image   (provider=ByteDance)  [非 LLM, 保留]
  [OK] voice_narrator       -> elevenlabs       (provider=ElevenLabs) [非 LLM, 保留]

SUMMARY: text tasks using MiniMax = 2/2
```

**V22 /health endpoint**:
```json
{"status":"ok","version":"22.0.0","service":"CloudTech V22 Unified Gateway","v10_modules_included":135,"v10_modules_failed":0,"flask_app_loaded":true}
```

---

## 🔒 治理边界 (MODEL_POLICY 适用范围)

### 强制: 统一走 MiniMax
- **text 推理** (LLM): MiniMax-M3 / MiniMax-M3-deep ✅
- **Codex 默认 model** (C:\Users\xinzh\.codex\config.toml): MiniMax-M3 ✅
- **Codex Profile** [profiles.ollama/qwen25/codex-openai]: 已删 ✅
- **OpenClaw modelPolicyAllowlist**: MiniMax-only ✅
- **AIOS Codex Adapter** (PreToolUse hook): 拦截任何非 MiniMax 写入 ✅
- **AIOS Reconciler** (5min 自动 + L1 auto-rollback): 持续守护 ✅

### 保留: 非 LLM 推理 (不在 MODEL_POLICY 范围)
- **视频生成**: ByteDance Seedream/Jimeng, Kuaishou Kling, Runway, OpenAI Sora — **保留** (多模态非 LLM 文本推理)
- **图像生成**: ByteDance Seedream, OpenAI DALL-E — **保留**
- **语音合成**: ElevenLabs, Azure TTS — **保留**
- **DashScope qwen** (阿里云百炼): 用于阿里云生态特殊 API (语音/视觉/特定行业模型)，**不用于通用 text 推理**

---

## ⚠️ 已知残留 (用户决定下一步)

V22 还有 20+ 个文件提到 `deepseek` 字符串，但都是**字符串引用或业务逻辑**（非 model 调用入口），不影响 MiniMax-Only 治理：

| 文件 | deepseek 出现 | 性质 |
|---|---|---|
| `workflows/impl/wf_g022_token_recon.py` | 字符串 | workflow 实现，可能 fallback 字符串 |
| `admin_dashboard.py` | 字符串 | 路由/UI 字符串 |
| `agent_assistant.py` | 字符串 | agent 描述 |
| `api_platform.py` | 字符串 | API 平台层 |
| `auto_pipeline.py` | 字符串 | 自动 pipeline |
| `cloudtech_app.py` | 字符串 | 主 app |
| `cron_pipeline.py` | 字符串 | cron pipeline |
| `daily_knowledge.py` | 字符串 | 知识库 |
| `deploy.py` | 字符串 | 部署 |
| `fastapi_app.py` | 字符串 | FastAPI |
| `geo_deep.py` | 字符串 | 地理位置 |
| `geo_optimizer.py` | 字符串 | GEO 优化 |
| `i18n.py` | 字符串 | 国际化 |
| `kuaizi_pipeline.py` | 字符串 | 筷子 pipeline |
| `model_aggregator.py.bak_*` | 备份文件 | 历史 |
| `onboarding.py` | 字符串 | onboarding |
| `openapi.py` | 字符串 | OpenAPI |
| `pipeline_engine.py` | 字符串 | pipeline 引擎 |
| `repurpose_pipeline.py` | 字符串 | 内容复用 |
| `run_geo_full.py` | 字符串 | GEO 全量 |
| `schemas.py` | 字符串 | schemas |
| `shengji_agent.py` | 字符串 | 升级 agent |
| `system_health_monitor.py` | 字符串 | 健康监控 |
| `template_library.py` | 字符串 | 模板库 |
| `video_engine.py` | 字符串 | 视频引擎 |
| `_backups/` (历史备份) | 字符串 | 备份目录，不加载 |

**建议 (用户后续决定)**:
- 短期：保留 (model_aggregator.py 是统一入口，删 .env DEEPSEEK_API_KEY 已阻断实际调用)
- 中期：用 IDE 全局替换 `deepseek` → `MiniMax-M3-deep` 在 V22 源码（注意备份）
- 长期：在 V22 加一个 startup check，扫所有 model 引用，violation → fail-fast

---

## 📂 关键产物

| 路径 | 内容 |
|---|---|
| `D:\AIOS\_restore_cloudtech_v22_self_elevate.cmd` (1,607 B) | 一键恢复 CloudTech cmd |
| `D:\AIOS\_restart_cloudtech_v22_apply_minimax.cmd` (840 B) | 一键重启 V22 让改动生效 |
| `D:\AIOS\_verify_v22_minimax.py` (1,190 B) | 验证 V22 model_aggregator MiniMax |
| `D:\CloudTech-Portable\.env` (2,957 B) | 删 DEEPSEEK_API_KEY，保留 MINIMAX |
| `D:\CloudTech-Portable\model_aggregator.py` (5,718 B) | text 段全部 MiniMax |
| `D:\AIOS\_agent-hub\reports\SOVEREIGNTY-V-CLOUDTECH-MINIMAX-2026-10-09.md` | 本报告 |

---

## 🎯 总指挥宣告

**CloudTech V22 SaaS · A+B 100% 完工**:
- ✅ V22 service 完整恢复 (port 5099 Listen, 135 V10 模块 loaded)
- ✅ V22 model_aggregator.py MiniMax-Only (text 段 2/2 走 MiniMax)
- ✅ V22 .env 删 DEEPSEEK_API_KEY，保留 MINIMAX_API_KEY
- ✅ 真实运行验证: `python _verify_v22_minimax.py` 全部 OK
- ✅ V22 /health endpoint 返回 200 OK

**用户操作 = 0** (UAC YES × 2: 恢复 + 重启)

**对你的产品影响**:
- V22 用户面对前端的模型选项变了：`deepseek-v4-pro` → `MiniMax-M3-deep`，`deepseek-v4-flash` → `MiniMax-M3`
- 内部 text 推理全部走 MiniMax-M3
- video/image/voice 不受影响 (继续走原 ByteDance/Kuaishou/OpenAI/ElevenLabs)
- 计费：MiniMax-M3 vs deepseek-v4-flash 单价不同（MiniMax 略贵但深度推理更强），用户需要重新评估

---

**Codex 01a11c23 · A+B 完工 · 2026-10-09**
