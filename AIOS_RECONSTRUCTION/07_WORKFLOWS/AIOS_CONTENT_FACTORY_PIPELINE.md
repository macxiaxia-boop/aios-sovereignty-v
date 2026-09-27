# AIOS Content Factory Pipeline · R212 STEP 15 · 2026-09-26

> **spec#17 Content Factory Pipeline** — 选题→脚本→生成→剪辑→发布→数据回流→复盘
> **基于**: R212 STEP 14 Video Pipeline skill (已落地) + 4 行业业务主线
> **触达红线**: #22 #29 #60 #95 #101 #103

---

## 1. 7 阶段闭环

```
选题 → 脚本 → 生成 → 剪辑 → 发布 → 数据回流 → 复盘
  ↑                                    ↓
  └────────────── 沉淀回知识库 ────────┘
```

---

## 2. 阶段定义

### 阶段 1 · 选题 (Topic)
**输入**: 行业关键词 + 用户痛点 + 趋势雷达
**方法**:
- L1: 内部数据(已拆解 6029 视频 12 博主) + 内容信号宪法(#17) - 高分内容复用
- L2: WebSearch Tier B (GitHub Trending + Product Hunt) + Tier E (Bilibili/抖音热榜)
- L3: 用户原话权威(#101) - 直接采纳用户提的选题
**输出**: topic.json { title, angle, target_audience, hook_idea, sources }

### 阶段 2 · 脚本 (Script)
**输入**: topic.json + 选博主风格样本 (从已拆解 .md)
**方法**:
- Ollama qwen3:14b (thinking) - 调 prompt 模板 + few-shot 博主文风样本
- Prompt 模板复用 v13 phase3 PROMPT 12 维结构反向(从结构到内容)
**输出**: script.md { 开头钩子(0-3s) + 主体 + 结尾 CTA, 字数 800-1500 }

### 阶段 3 · 生成 (Generate)
**输入**: script.md
**方法**:
- TTS: edge-tts / GPT-SoVITS (本地, 0 成本) / 阿里云 CosyVoice (云, 0.5元/万字)
- 画面: 即梦 AI / 可灵 AI / Pika / AtlasCloud mcp__atlascloud (按 spec#22 优先级)
- B-Roll: Pexels API (免费) + AI 图 (atlas_generate_image)
**输出**: raw_video.mp4 (无声/有音轨) + 字幕 SRT

### 阶段 4 · 剪辑 (Edit) ← R212 STEP 14 复用
**输入**: raw_video.mp4 + script.md (作为 timing 参考)
**方法**:
- ffmpeg + faster-whisper-large-v3.5 (P2) - 校对字幕
- jump cut (去沉默) + filler word 检测 + 缩放 + 转场
- 封面: cover_3bloggers_ollama.py (D:\AIOS\_workzone 已有脚本)
**输出**: final_video.mp4 + cover.jpg + subtitles.srt + meta.json

### 阶段 5 · 发布 (Publish)
**输入**: final_video.mp4 + 平台账号列表
**方法**:
- 小红书/抖音/视频号/B站/公众号多平台
- 矩阵号 17 账号 (R200 制图 SOP v1.0)
- 平台 API 调度 (头条开放平台 / 巨量百应 / 微信公众平台)
- 发布时间矩阵化 (早 7-9 / 中 12-14 / 晚 19-22 三时段)
**输出**: publish_log.json { platform, url, post_time, video_id }

### 阶段 6 · 数据回流 (Analytics)
**输入**: publish_log.json + 平台 webhook
**方法**:
- 抖音/小红书数据 API (播放/点赞/评论/完播率/转化)
- 评论关键词 NLP (qwen3:14b 分析用户反馈)
- 转化追踪 (留资 / 加微 / 私信 / 留电话)
**输出**: analytics.json { video_id, metrics, comments_nlp, conversions }

### 阶段 7 · 复盘 (Retrospective)
**输入**: analytics.json + topic.json + script.md
**方法**:
- 12 维结构评分 (复用 spec#15-16 拆解维度)
- 与历史 TOP 10 对比
- 沉淀到 知识库: 高分内容复用 / 低分内容 avoid
- Skill 自动生成: 高复用模式 -> 新 skill (`sk-topic-predict`, `sk-hook-pattern`)
**输出**: retro.md + skill_candidate.json

---

## 3. Skill 标准结构

每个 Content Factory 子 skill 必须包含:

```yaml
skill_id: sk-{phase}-{subtask}
version: 1.0.0
inputs:
  - name: blog_topic
    type: object
    required: true
outputs:
  - name: result
    type: object
phases:
  - id: pre_check
    cmd: ...prereq
  - id: main
    cmd: ...action
  - id: post_check
    cmd: ...evidence
evidence_required: true
test_data: tests/{skill_id}/input_sample.json
expected_output: tests/{skill_id}/expected.json
fallback_chain:
  - primary: qwen3:14b
  - secondary: qwen2.5:3b
  - tertiary: human_handoff
```

---

## 4. 与 Video Pipeline skill 的关系

| 维度 | Video Pipeline | Content Factory |
|---|---|---|
| 输入 | 原始 mp4 | 选题 topic |
| 输出 | md 12 维拆解 | 成片 + 发布 + 数据 |
| 阶段 | 3 (P1/P2/P3) | 7 (选题到复盘) |
| 复用 | v13 R230 | Video Pipeline P1+P2+P3 |
| 用户 | 拆解他人内容 | 生产自己内容 |

**Video Pipeline 是 Content Factory 的子集** (阶段 3-4)

---

## 5. 落地顺序 (P0 → P3)

### P0 (本周可做)
- [ ] sk-topic-predict: 选题预测 (基于 6029 已拆解数据 LLM 模式提取)
- [ ] sk-script-gen: 脚本生成 (qwen3:14b + 12 维 PROMPT)

### P1 (1 周)
- [ ] sk-cover-gen: 封面生成 (复用 _cover_3bloggers_ollama.py)
- [ ] sk-publish-scheduler: 多平台定时发布 (WinSW cron)

### P2 (2 周)
- [ ] sk-analytics-collect: 数据采集 (平台 API 集成)
- [ ] sk-comment-nlp: 评论 NLP (qwen3:14b)

### P3 (1 月)
- [ ] sk-skill-evolve: 复盘 → 新 skill 自动生成 (闭环)

---

## 6. 与 4 行业业务主线对接

| 行业 | 主要内容形态 | 主要平台 | 关键转化 |
|---|---|---|---|
| 装修/建材/装企 | 案例 + 知识科普 | 抖音/小红书/视频号 | 留资 → 上门量房 |
| 教育 | 课程切片 + 学员见证 | 抖音/视频号/B站 | 加微 → 体验课 |
| 制造 | 工厂实景 + 产品演示 | 抖音/视频号 | 询盘 → 1688 |
| 服务 | 流程透明化 + 用户证言 | 小红书/抖音 | 私信 → 预约 |

---

## 7. 触达红线

| 红线 | 触达 | 状态 |
|---|---|---|
| #22 L1/L5 | 设计文档 + skill stub (本地) | ✅ |
| #29 编码 by 文件类型 | UTF-8 (.md) | ✅ |
| #60 治本可验证 | spec#17 7 阶段 + 4 行业对接 | ✅ |
| #95 EXTEND 而非重建 | 复用 Video Pipeline skill | ✅ |
| #101 用户原话 | 用户 4 行业业务主线 | ✅ |
| #103 L1 穷尽 | 基于 R211 + STEP 14 实证 | ✅ |

---

## 8. 下一步

1. **P0 落地**: sk-topic-predict + sk-script-gen (2-3 天)
2. STEP 16: 12 Acceptance Tests (spec#82)
3. STEP 17: 修 br-aios-hermes PATH 冲突
4. STEP 14b: 批量补 P0 缺口 (陈厂长/高盖伦 P2 + 3 博主 P3)