# Skill 卸载报告 · arkcli + volcengine · 2026-10-09

> **任务**: 备份 + 卸载 arkcli + volcengine 29 skill (实测 30 个)
> **状态**: ✅ DONE — 30/30 已 archive, 0/30 残留 active
> **可逆性**: ✅ 完全可逆 (move 而非 delete, manifest 记录原路径)

---

## 卸载前扫描
```powershell
Get-ChildItem C:\Users\xinzh\.agents\skills -Directory -Filter 'arkcli-*'
# 25 个 arkcli-* skills

Get-ChildItem C:\Users\xinzh\.agents\skills -Directory -Filter 'volcengine-*'
# 5 个 volcengine-* skills
# 总计 30 (用户估算 29, 实际 +1)
```

### 30 skill 清单 (按字母序)

#### arkcli-* (25)
1. arkcli-agent
2. arkcli-api-explorer
3. arkcli-auth
4. arkcli-billing
5. arkcli-chat
6. arkcli-code-example
7. arkcli-config
8. arkcli-connect
9. arkcli-custommodel
10. arkcli-datasets
11. arkcli-deploy
12. arkcli-doctor
13. arkcli-gen
14. arkcli-helper
15. arkcli-infer-endpoint
16. arkcli-models
17. arkcli-onboard
18. arkcli-plans
19. arkcli-pricing
20. arkcli-profile
21. arkcli-resources
22. arkcli-shared
23. arkcli-train-finetune
24. arkcli-understand
25. arkcli-usage

#### volcengine-* (5)
1. volcengine-cli
2. volcengine-feedback
3. volcengine-find-skills
4. volcengine-knowledge-search
5. volcengine-troubleshooting

---

## 备份目标

```
C:\Users\xinzh\.agents\skills.archive.2026-10-09\
  arkcli-agent/                       (134,746 bytes)
  arkcli-api-explorer/                (15,008 bytes)
  arkcli-auth/                        (51,626 bytes)
  arkcli-billing/                     (21,125 bytes)
  ... (其余 26 个)
  volcengine-troubleshooting/
  00-manifest.json                    (snapshot 列表)
```

### manifest.json 格式
```json
[
  {
    "Name": "arkcli-agent",
    "OriginalPath": "C:\\Users\\xinzh\\.agents\\skills\\arkcli-agent",
    "ArchivePath": "C:\\Users\\xinzh\\.agents\\skills.archive.2026-10-09\\arkcli-agent",
    "SizeBytes": 134746
  },
  ...
]
```

---

## 卸载过程

### 操作
- 命令: `Move-Item -LiteralPath <original> -Destination <archive>` × 30
- 全部成功, 0 失败

### 验证
```
remaining arkcli-*: 0
remaining volcengine-*: 0
archive subdirs: 30
```

### 文件系统影响
- `C:\Users\xinzh\.agents\skills\` 减少 30 个目录 (~1 MB)
- `C:\Users\xinzh\.agents\skills.archive.2026-10-09\` 新增 30 个目录
- 总磁盘占用不变 (move 而非 copy)

---

## 对 Codex session 影响

### 预期
- Codex system context 加载 skill 列表会移除这 30 个
- 700+ skill 总数 → 670+ skill
- 本会话 Codex 启动时间应略减 (skill load 阶段跳过 30)

### 实测
- **本会话启动早于卸载**, 本次响应中 skill 列表已固定 (system context 缓存)
- **下次 Codex 重启后** 才会真正反映卸载效果

---

## 反向操作（如果需要恢复）

```powershell
$archive = 'C:\Users\xinzh\.agents\skills.archive.2026-10-09'
$target  = 'C:\Users\xinzh\.agents\skills'
Get-Content "$archive\00-manifest.json" | ConvertFrom-Json | ForEach-Object {
  Move-Item -LiteralPath $_.ArchivePath -Destination (Join-Path $target $_.Name) -Force
}
```

30 个 skill 完整还原, manifest 包含原始路径 + 大小信息.

---

## 验收

| 项 | 数字 | 状态 |
|---|---|---|
| arkcli-* archived | 25/25 | ✅ |
| volcengine-* archived | 5/5 | ✅ |
| total archived | 30/30 | ✅ |
| remaining in active dir | 0 | ✅ |
| manifest written | 1 | ✅ |
| 磁盘占用变化 | 0 (move) | ✅ |

---

## 红线遵守

- ✅ **Move 不 Delete** — 完全可逆
- ✅ Manifest 记录所有原路径
- ✅ 没改任何 skill 内容 (仅移动目录)
- ✅ 没动 policy v2 / kernel/

---

## 后续建议

### 如果用户确认 arkcli/volcengine 真不用
- 等下次 Codex 重启, 验证系统 context 不再含这 30 个
- T4 分类矩阵更新: 把 `arkcli-*` 24 + `volcengine-*` 5 从"已加载"清单移除

### 如果用户决定恢复
- 跑上面的 PowerShell 反向脚本

### 如果发现某个 skill 真要用 (如 arkcli-deploy, arkcli-billing)
- 选择性从 archive 移回 (单条, 不需要全部恢复)

---

_— Codex (supervisor) · Q4 完成 · 30/30 skill archived · 0 残留 · manifest 完整 · 2026-10-09_