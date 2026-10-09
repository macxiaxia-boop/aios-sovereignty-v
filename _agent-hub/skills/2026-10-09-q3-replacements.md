# Q3 · 7 个 P0 Marketing 替代品启用清单 · 2026-10-09

> **任务**: 7 个替代品 (4 个原命名 skill 缺失, 用已安装替代品)
> **方法**: 不装新 skill, 在 `.agents/skills/` 加 active 标记 (在本文件 + `.agents/skills/_active_p0.json`)
> **验收**: 8/8 (含 `demand-acquisition`) 替代品目录存在 + active 标记

---

## 8 个 P0 Marketing 武器启用清单 (实测目录)

| 原 P0 名 | 替代 (实际目录) | 路径 | 启用标记 |
|---|---|---|---|
| `marketing-demand-acquisition` | `demand-acquisition` | `C:\Users\xinzh\.agents\skills\demand-acquisition\` | ✅ active |
| `competitor-research-global` | `competitor-intel` | `C:\Users\xinzh\.agents\skills\competitor-intel\` | ✅ active |
| `competitor-research-global` | `competitor-profiling` | `C:\Users\xinzh\.agents\skills\competitor-profiling\` | ✅ active |
| `competitor-research-global` | `competitors` | `C:\Users\xinzh\.agents\skills\competitors\` | ✅ active |
| `competitor-research-global` | `competitors-alt` | `C:\Users\xinzh\.agents\skills\competitors-alt\` | ✅ active |
| `competitor-research-global` | `mkt-competitor-analysis` | `C:\Users\xinzh\.agents\skills\mkt-competitor-analysis\` | ✅ active |
| `customer-insight-global` | `customer-research` | `C:\Users\xinzh\.agents\skills\customer-research\` | ✅ active |
| `customer-insight-global` | `reddit-insights` | `C:\Users\xinzh\.agents\skills\reddit-insights\` | ✅ active |
| `channel-setup-global` | `influencer-marketing` | `C:\Users\xinzh\.agents\skills\influencer-marketing\` | ✅ active |

**总 active = 9** (1 用户在贴索 + 8 替代品, 含 competitor-research-global 5 替代 + customer 2 替代 + channel 1 替代)

---

## active 标记机制

### 不修改 `_meta.json` (避免破坏 skill loader 格式)
- Codex skill loader 期望的 `_meta.json` 字段是 `name`, `description`, `version`, `tags`, `requires`, `install_path`
- 加 `active: true` 是非标准字段, 可能破坏 loader 校验

### 改用独立 registry
- 新建 `C:\Users\xinzh\.agents\skills\_active_p0.json`
- Codex session 启动时可读这个 registry 做"启用检查" (本会话内)

---

## Registry 内容

```json
{
  "version": 1,
  "created_at": "2026-10-09",
  "author": "codex-supervisor",
  "rationale": "Q3 启用 5 个 P0 marketing 重武器 · 4 个命名错位, 用 8 替代品补齐",
  "active_skills": [
    {"original_name": "marketing-demand-acquisition", "installed_as": "demand-acquisition", "path": "C:\\Users\\xinzh\\.agents\\skills\\demand-acquisition", "verified_at": "2026-10-09"},
    {"original_name": "competitor-research-global", "installed_as": "competitor-intel", "path": "C:\\Users\\xinzh\\.agents\\skills\\competitor-intel", "verified_at": "2026-10-09"},
    {"original_name": "competitor-research-global", "installed_as": "competitor-profiling", "path": "C:\\Users\\xinzh\\.agents\\skills\\competitor-profiling", "verified_at": "2026-10-09"},
    {"original_name": "competitor-research-global", "installed_as": "competitors", "path": "C:\\Users\\xinzh\\.agents\\skills\\competitors", "verified_at": "2026-10-09"},
    {"original_name": "competitor-research-global", "installed_as": "competitors-alt", "path": "C:\\Users\\xinzh\\.agents\\skills\\competitors-alt", "verified_at": "2026-10-09"},
    {"original_name": "competitor-research-global", "installed_as": "mkt-competitor-analysis", "path": "C:\\Users\\xinzh\\.agents\\skills\\mkt-competitor-analysis", "verified_at": "2026-10-09"},
    {"original_name": "customer-insight-global", "installed_as": "customer-research", "path": "C:\\Users\\xinzh\\.agents\\skills\\customer-research", "verified_at": "2026-10-09"},
    {"original_name": "customer-insight-global", "installed_as": "reddit-insights", "path": "C:\\Users\\xinzh\\.agents\\skills\\reddit-insights", "verified_at": "2026-10-09"},
    {"original_name": "channel-setup-global", "installed_as": "influencer-marketing", "path": "C:\\Users\\xinzh\\.agents\\skills\\influencer-marketing", "verified_at": "2026-10-09"}
  ]
}
```

---

## 反向 kpi 替代

**`reverse-kpi-global` 无直接替代**:
- Skill 列表中无 `reverse-kpi*` 或 `kpi-reverse*` 或类似命名
- 业务侧实现建议:
    1. 用 `pricing-strategy` 反推定价
    2. 用 `ceo-advisor` / `cmo-advisor` 反推预算
    3. 跑 `business-model-canvas` 类工具

**decision**: `reverse-kpi-global` 留 P0 占位但**无替代**, 等用户后续决定装原版或写新 skill

---

## 验收

| 项 | 数字 | 状态 |
|---|---|---|
| 替代品目录存在 | 8/8 | ✅ |
| registry 写入 | 1 file | ✅ |
| active 标记 | 9/9 (含原 demand-acquisition) | ✅ |
| 原命名 skill 装 | 0/4 (用户已知道不用装) | ✅ |

---

## 不做的事

- ❌ 不装 4 个原命名 skill (`competitor-research-global` 等)
- ❌ 不改任何 `_meta.json` 文件
- ❌ 不删任何 skill

---

_— Codex (supervisor) · Q3 完成 · 8 替代品启用 · 1 原 P0 (reverse-kpi) 占位无替代 · 2026-10-09_