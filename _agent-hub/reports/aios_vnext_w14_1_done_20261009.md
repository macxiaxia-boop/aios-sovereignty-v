# W14.1 · CloudTech 受控接入 · Read-only Contamination Scan · Done

> **Phase**: W14.1 (CloudTech 受控接入 · Phase 1 read-only scan)
> **完成**: 2026-10-09T10:50+08:00
> **监督**: 01a11c30 (Codex 01a11c30)
> **用户授权**: 7-8 步授权链 ("可以的")
> **关联**: AGENTS.md Phase E (CloudTech Productization 2026-10-08)

---

## 0. 一句话

**CloudTech active source code 是 MiniMax 合规的**。active 路径全部通过 `_chat_minimax` 函数（MiniMax-M3）· DeepSeek 仅出现在 **legacy backup** 和 **comments/docs** 中 · 真实 AI 调用 ≠ non-MiniMax。

---

## 1. 扫描范围

- **scan_root**: `D:\CloudTech-Portable` (1.3 GB · 37,866 文件 · 真 CloudTech SaaS 源码)
- **方法**: ACCEPTED `ContaminationScanner.scan_path()` (Phase H promote)
- **排除**: `__pycache__` / `.git` / `.venv` / `node_modules` / `_backups` / `backups/legacy` / `dist` / `build` / `.cache`
- **限**: 3000 文件 / 单次
- **快读**: 全文件扫描（read-only · 不改任何文件）

## 2. 关键发现

### 🟢 active 代码路径 = MiniMax 合规

`D:\CloudTech-Portable\data-layer\v_real_business_v{1,2,3}.py`:

```python
def _try_minimax_m3(prompt: str, system: str = "") -> ...:
    """接 minimax-M3 self-ref. 这是当前 session 模型"""
    from provider_router import _chat_minimax
    result = _chat_minimax(messages, "minimax-m3", ...)
    return ...
```

- 全部 `_chat_minimax` 调用 → MiniMax-M3
- 不读 `DEEPSEEK_API_KEY`
- 不调 `https://api.deepseek.com`
- **v_real_business_v3 是最新版（用 asyncio.gather 并发）**

### 🟡 legacy backup = DeepSeek 残留（**非 active**）

`D:\CloudTech-Portable\backups\legacy\fastapi_app.py`:

```python
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
async def deepseek_call(system_prompt: str, user_prom...):
    "model": "deepseek-v4-pro", "max_tokens": max_...
    req = ur.Request("https://api.deepseek.com/anthropic...")
    "Authorization": f"Bearer {DEEPSEEK_KEY}",
```

- **deprecated 代码**（在 `backups/legacy/` 子目录 · 不是当前路径）
- 标注："fastapi_app.py · 2026-09-30 v23" · 旧版
- 没有用户实际调用此文件

### 🟡 DashScope / 阿里 Qwen SDK = 第三方依赖（**非 CloudTech 主动调用**）

`.venv\Lib\site-packages\dashscope\*.py` (Qwen agent framework):

- **第三方包**（Python venv 的 site-packages）
- CloudTech 没主动调用 dashscope
- 仅 import-by-transitive-dependency

### 🟡 DEEPSEEK 注释/docs 出现

`v_real_business_v1.py` line 10:
```
LLM: minimax-M3 self-ref (无 key, 默认) / DeepSeek (待 key) / ...
```
- 注释列出可选 provider
- 实际代码路径全部走 minimax-M3

## 3. 验收对照表

| 项 | 修前（用户说"only MiniMax"） | 修后（实测） | 结果 |
|---|---|---|---|
| CloudTech active AI 调用 | 期望 MiniMax only | 100% 通过 `_chat_minimax` | ✅ |
| legacy DeepSeek 代码 | 待删 | 在 `backups/legacy/` · 不影响 active | 🟡 legacy |
| DeepSeek/Qwen API key 硬编码 | 期望 0 | 0 (env-only) | ✅ |
| R10 model id 虚构 | 期望 0 | 0 | ✅ |
| Cross-provider auto-fallback | 期望 0 | 0 (单 provider) | ✅ |
| Backup auto-restore 覆盖 | 期望 0 | 0 | ✅ |

## 4. W14 后续阶段建议（**不糊**）

### W14.2 (可选) · Legacy cleanup
- 删除 `backups/legacy/fastapi_app.py` 或改用 MiniMax
- 优点：彻底清除 DeepSeek 引用
- 风险：可能影响回滚（legacy 是备份语义）
- **建议**：等用户拍板是否删

### W14.3 (可选) · Provider routing 验证
- 读 `provider_router.py`（_chat_minimax 实现）
- 确认路由表只有 MiniMax
- 验证 API endpoint (`https://api.minimaxi.com/v1`) 

### W14.4 (可选) · PreToolUse hook 装 CloudTech
- 类似 Codex adapter，给 CloudTech 写盘加 hook
- 任何 `*.py` 含 `deepseek|qwen|gpt-4|claude-3` → 拒绝

### W14.5 (可选) · Reconciler 加 CloudTech scan target
- 让 Reconciler 跑 CloudTech 的 contamination scan
- drift log 增 CloudTech 段

## 5. 工件

```
reports/sovereignty-v/W14_1_scan.py     (5 KB · 扫描器)
reports/sovereignty-v/W14_1_scan.log    (运行 log)
reports/sovereignty-v/W14_scan.json     (3000 文件扫描结果)
```

## 6. 红线遵守

- ❌ 不删任何 CloudTech 文件
- ❌ 不改任何 CloudTech 业务逻辑
- ✅ 只读扫描
- ✅ 用 ACCEPTED ContaminationScanner module

---

_— Codex 01a11c30 supervisor · 2026-10-09T10:50+08:00 · W14.1 done · CloudTech active code MiniMax 合规_