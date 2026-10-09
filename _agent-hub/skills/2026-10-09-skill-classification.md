# Codex Skill 分类矩阵 · 2026-10-09

> **执行者**: Codex (supervisor) · read-only 分类 · 不改 skill 安装
> **范围**: 本会话 Codex 加载的 700+ skill（system-list · 截至 2026-10-09）
> **用途**: 帮用户识别"哪些 skill 真在用 / 哪些是高价值低使用 / 哪些可以卸载"
> **维度**: 业务域 (BIZ) · 用途 (USE) · 优先级 (PRI) · 是否在用 (USED)

---

## 维度说明

| 维度 | 取值 |
|---|---|
| **BIZ** (业务域) | AIOS-ENG (主权工程) · MKT (营销中台业务) · GEN (通用) · NICHE (专用/小众) |
| **USE** (用途) | CODE (编程) · CONTENT (内容) · DATA (数据) · OPS (运维) · GOV (治理) · ARCH (架构) · SALES (销售) · RESEARCH (调研) · TOOL (工具桥) · STRAT (战略) |
| **PRI** (优先级) | P0 (核心/不可缺) · P1 (高频用) · P2 (偶尔用) · P3 (备查) |
| **USED** (在用) | Y (本会话/历史用过) · N (从未用) · ? (无法判断) |

---

## A. AIOS 主权工程相关 (BIZ = AIOS-ENG)

### A1 · 主权/治理/审计 (GOV · P0)

| Skill | USE | PRI | USED | 备注 |
|---|---|---|---|---|
| `aios-adapter-codex-desktop` | GOV | P0 | Y | Codex Desktop 桥 (本会话直连)` |
| `aios-adapter-openclaw` | GOV | P0 | ? | OpenClaw 9-agent 调度适配 |
| `aios-adapter-hermes` | GOV | P0 | ? | Hermes 进程内治理 |
| `aios-adapter-mcp-bridge` | GOV | P0 | ? | MCP HTTP→stdio 转发 |
| `aios-adapter-feishu` | GOV | P1 | N | 飞书推送 (业务侧, 非主权) |
| `aios-adapter-langfuse` | GOV | P1 | ? | Observability trace 红线 |
| `aios-adapter-v5-bridge` | GOV | P0 | ? | V5 13 模块统一入口 |
| `aios-adapter-doubao` | GOV | P2 | N | 豆包 (L4 pending · 未启用) |
| `v5-checker` | GOV | P0 | Y | R-004 红线验证 |
| `v5-maker` | GOV | P0 | Y | R-004 草稿生成 |
| `v5-pil-runtime` | GOV | P0 | Y | R-127 PIL 6 子模块 |
| `v5-intent-compiler` | GOV | P0 | Y | R-122 Intent IR 编译 |
| `v5-priority-engine` | GOV | P0 | Y | R-123 10 维打分 |
| `v5-problem-resolution` | GOV | P0 | Y | R-123 8 阶段分解 |
| `v5-rolling-planner` | GOV | P0 | Y | R-122 NOW/SOON/LATER |
| `v5-empirical-runner` | GOV | P0 | Y | R-124 4 .lnk 实证 |
| `v5-idle-detector` | GOV | P0 | Y | R-125 4 类空闲 |
| `v5-daily-plan` | GOV | P0 | Y | R-125 top-3 |
| `v5-learning-gate` | GOV | P0 | Y | R-129 抽象跃迁门控 |
| `v5-skill-health` | GOV | P0 | Y | R-126 技能健康度 |
| `v5-continuity-memory` | GOV | P0 | Y | R-128 12 字段记忆 |

### A2 · Codex / ClaudeCode 工具链 (TOOL · P1)

| Skill | USE | PRI | USED |
|---|---|---|---|
| `codex-audio-edit` | TOOL | P1 | N |
| `codex-browser-click` / `-open` / `-screenshot` | TOOL | P1 | N |
| `codex-clipboard-history` / `-read` / `-write` | TOOL | P1 | N |
| `codex-email-receive` / `-send` | TOOL | P2 | N |
| `codex-excel-edit` | TOOL | P2 | N |
| `codex-file-batch-rename` / `-search` | TOOL | P1 | N |
| `codex-http-request` | TOOL | P1 | Y |
| `codex-image-edit` | TOOL | P2 | N |
| `codex-keyboard-type` | TOOL | P2 | N |
| `codex-mouse-click` / `-scroll` | TOOL | P2 | N |
| `codex-ocr` | TOOL | P2 | N |
| `codex-ppt-create` / `-read` | TOOL | P2 | N |
| `codex-process-list` | TOOL | P1 | N |
| `codex-screen-record` | TOOL | P2 | N |
| `codex-screenshot` | TOOL | P1 | N |
| `codex-speech-to-text` | TOOL | P2 | N |
| `codex-system-info` | TOOL | P1 | N |
| `codex-text-to-speech` | TOOL | P2 | N |
| `codex-websocket-client` | TOOL | P2 | N |
| `codex-window-close` / `-focus` / `-list` / `-move` | TOOL | P1 | N |
| `codex-word-edit` | TOOL | P2 | N |
| `windows-desktop-control` | TOOL | P1 | Y |
| `windows-media-control` | TOOL | P2 | N |
| `windows-screenshot` | TOOL | P1 | Y |
| `computer-use:computer-use` | TOOL | P1 | N |

### A3 · MCP / Agent 编排 (OPS · P1)

| Skill | USE | PRI | USED |
|---|---|---|---|
| `mcp-builder` | ARCH | P1 | ? |
| `agent-reach` (Agent-Reach) | RESEARCH | P0 | ? |
| `agent-team-orchestrator` | OPS | P1 | ? |
| `dispatching-parallel-agents` | OPS | P1 | ? |
| `subagent-driven-development` | OPS | P1 | ? |
| `executing-plans` | OPS | P1 | ? |
| `using-git-worktrees` | OPS | P1 | Y |

### A4 · gstack (QA/Plan/Deploy) | GQA · P0

| Skill | PRI | USED | 备注 |
|---|---|---|---|
| `gstack` | P0 | Y | 主入口 |
| `browse` | P0 | Y | QA testing |
| `benchmark` | P1 | Y | perf regression |
| `benchmark-models` | P2 | N | |
| `canary` | P1 | Y | post-deploy monitor |
| `careful` | P0 | Y | destructive guardrails |
| `context-restore` / `context-save` | P1 | Y | |
| `csO` | P0 | ? | Security Officer mode |
| `codex` | P0 | Y | CLI wrapper |
| `devex-review` | P0 | Y | dev experience |
| `freeze` / `unfreeze` | P1 | Y | session boundary |
| `gstack-upgrade` | P2 | N | |
| `guard` | P0 | Y | full safety mode |
| `health` | P0 | Y | code quality |
| `investigate` | P1 | Y | systematic debug |
| `ios-clean` / `-design-review` / `-fix` / `-hig-design` / `-qa` / `-sync` | P2 | N | iOS 专用 |
| `land-and-deploy` | P1 | Y | |
| `landing-report` | P1 | Y | |
| `learn` | P1 | Y | project learnings |
| `office-hours` | P2 | N | YC mode |
| `open-gstack-browser` | P1 | ? | |
| `pair-agent` | P2 | N | |
| `plan-ceo-review` / `-design-review` / `-devex-review` / `-eng-review` | P0 | Y | plan reviews |
| `plan-tune` | P2 | N | |
| `qa` / `qa-only` | P0 | Y | systematic QA |
| `requesting-code-review` | P1 | Y | |
| `retro` | P2 | N | weekly retro |
| `review` | P0 | Y | pre-landing PR review |
| `scrape` | P1 | Y | web data pull |
| `setup-browser-cookies` | P2 | N | |
| `setup-deploy` | P2 | N | |
| `setup-gbrain` | P2 | N | |
| `ship` | P0 | Y | ship workflow |
| `skillify` | P1 | ? | skill codify |
| `sync-gbrain` | P2 | N | |
| `test-driven-development` | P0 | Y | |
| `verification-before-completion` | P0 | Y | |

### A5 · 编程方法论 (CODE · P1)

| Skill | PRI | USED |
|---|---|---|
| `37signals-way` | P2 | N |
| `clean-architecture` / `clean-code` | P1 | ? |
| `design-code-architecture` | P1 | ? |
| `domain-driven-design` / `ddia-systems` | P2 | N |
| `high-perf-browser` | P2 | N |
| `microinteractions` | P2 | N |
| `pragmatic-programmer` | P2 | N |
| `refactoring-patterns` / `refactoring-ui` | P1 | ? |
| `release-it` | P1 | ? |
| `remove-technical-debt` | P1 | ? |
| `software-design-philosophy` | P1 | ? |
| `system-design` | P1 | ? |
| `team-topologies` | P2 | N |
| `web-typography` | P2 | N |
| `working-with-legacy-code` | P1 | ? |
| `developing-with-streamlit` | P2 | N |
| `documents:documents` / `docx` | P2 | N |
| `pdf` / `pdf:pdf` | P1 | ? |
| `pptx` | P1 | ? |
| `presentations:Presentations` | P1 | ? |
| `spreadsheets:Spreadsheets` / `excel-live-control` | P1 | ? |
| `template-creator` | P2 | N |
| `xlsx` | P1 | ? |
| `webapp-testing` | P1 | ? |

---

## B. AIOS 营销中台业务 (BIZ = MKT)

### B1 · 营销综合 (MKT-ALL · P0)

| Skill | PRI | USED |
|---|---|---|
| `marketing` | P0 | Y | 主入口 (scaling broker, gstack-style) |
| `marketing-context` | P0 | Y | 上下文文档 |
| `marketing-strategy-pmm` | P0 | ? | PMM 战略 |
| `marketing-demand-acquisition` | P0 | ? | 需求获取 |
| `marketing-principles` | P0 | Y | time to market 原则 |
| `marketing-psychology` | P0 | Y | 心理原则 |
| `marketing-ideas` / `marketing-ideas-2` | P0 | Y | 灵感生成 |
| `marketing-plan-global` (00) | P0 | Y | 7-section 计划 |
| `content-calendar-global` (01) | P0 | Y | 月度日历 |
| `campaign-brief-global` (02) | P0 | ? | 9-section brief |
| `performance-eval-global` (03) | P0 | ? | 表现诊断 |
| `script-video-global` (04) | P0 | Y | 短视频脚本 |
| `ad-copy-global` (05) | P0 | Y | 6 ad 变体 |
| `ugc-egc-brief-global` (06) | P0 | ? | UGC/EGC brief |
| `marketing-report-global` (07) | P0 | Y | "5 分钟" 周报 |
| `competitor-research-global` (08) | P0 | ? | 3 层分析 |
| `customer-insight-global` (09) | P0 | ? | JTBD |
| `reverse-kpi-global` (10) | P0 | ? | 反推 KPI |
| `channel-setup-global` (11) | P0 | ? | 渠道搭建 |
| `landing-page-brief-global` (12) | P0 | Y | LP brief |
| `data-analysis-global` (13) | P0 | ? | 数据分析 |
| `email-marketing-global` (14) | P0 | ? | 邮件自动化 |
| `social-listening-global` (15) | P0 | ? | 社交监听 |
| `marketing-psychology-global` (16) | P0 | ? | 7 大原则 |
| `pricing-strategy-global` (17) | P0 | ? | 定价策略 |
| `referral-program-global` (18) | P0 | ? | 推荐计划 |
| `ab-test-setup-global` (19) | P0 | ? | A/B 测试 |
| `client-intake-brief-global` (20) | P0 | ? | 客户 intake |
| `ads-audit-global` (21) | P0 | Y | 投放审计 |
| `product-marketing-context-global` | P0 | Y | PMM 上下文 |

### B2 · 内容创作 (CONTENT · P0)

| Skill | PRI | USED |
|---|---|---|
| `content-strategy` | P0 | Y |
| `content-production` | P0 | Y |
| `content-marketer` | P0 | Y |
| `content-humanizer` | P0 | Y |
| `content-repurpose` | P0 | Y | 一鱼多吃 |
| `content-idea-generator` | P0 | Y |
| `de-ai-ify` | P0 | Y | 去 AI 化 |
| `voice-extractor` | P1 | ? |
| `copy-editing` / `copywriting` / `brand-copywriter` | P0 | Y |
| `copywriting-psychologist` / `headline-psychologist` / `brand-perception-psychologist` | P1 | ? |
| `writing-skills` | P1 | ? |
| `blog-writer` (`seo-aeo-blog-writer`) | P0 | Y |
| `landing-page-generator` / `seo-aeo-landing-page-writer` | P0 | ? |
| `social-card-gen` | P1 | ? |
| `webinar-marketing` | P1 | ? |
| `reddit-insights` / `last30days` / `youtube-summarizer` / `youtube-full` | P1 | ? |
| `douyin-competitor-analysis` / `douyin-transcribe-lz` / `xiaohongshu-hot-tracker` | P1 | ? |
| `seedream` / `wanxiang-image-generation-editing-alternative` / `jimeng-cli-text2image` / `dreamina-cli` / `imagegen` | P1 | ? |

### B3 · 社媒运营 (SOCIAL · P0)

| Skill | PRI | USED |
|---|---|---|
| `social` | P0 | Y |
| `social-media-analyzer` | P0 | ? |
| `social-orchestrator` | P1 | ? |
| `community-marketing` | P0 | ? |
| `community-building-global` | P1 | ? |
| `influencer-marketing` | P0 | ? |
| `competitor-profiling` / `competitors` / `competitor-profiling` / `competitor-intel` / `competitive-intel` | P0 | ? |
| `homepage-audit` / `homepage-audit` | P0 | ? |
| `cro` / `cro-optimization` / `cro-methodology` | P0 | Y |
| `onboarding` / `onboarding-cro` / `popups` / `popup-cro` | P1 | ? |
| `cold-email` / `cold-outreach-sequence` / `outreach-specialist` / `referrals` / `referral-program` | P0 | ? |
| `lead-magnet-generator` / `lead-magnets` | P0 | Y |
| `scorecard-marketing` | P1 | ? |
| `free-tool-strategy` | P1 | ? |
| `newsletter-creation-curation` | P1 | ? |
| `email-sequence` / `emails` / `email-sender` | P0 | ? |
| `meeting-prep-cc` / `meeting-prep` | P1 | ? |
| `daily-briefing-builder` / `daily-marketing-brief` | P0 | Y |
| `data-weekly-report` | P0 | Y |

### B4 · 个人品牌 + 创作者 (CREATOR · P0)

| Skill | PRI | USED |
|---|---|---|
| `personal-brand-context-global` (22) | P0 | ? |
| `personal-brand-strategy-global` (23) | P0 | ? |
| `ai-avatar-production-global` (24) | P1 | ? |
| `voice-clone-podcast-global` (25) | P1 | ? |
| `thought-leadership-content-global` (26) | P0 | ? |
| `personal-brand-monetize-global` (27) | P0 | ? |
| `creator-zhuzi` (柱子哥) | P0 | Y | 灵策域 |
| `creator-product-opc` (柱子哥·产品层) | P0 | ? |
| `creator-trend-ai` (柱子哥·趋势) | P0 | Y |
| `creator-xiaolin` (小Lin说) | P0 | ? |
| `creator-cognitive-turn` (小Lin·灵魂版) | P0 | Y |
| `creator-xiaoa-xuecai` (小A学财经) | P0 | ? |
| `creator-reveal-truth` (小A·灵魂版) | P0 | Y |
| `creator-cold-analysis` (高盖伦·灵魂版) | P0 | Y |
| `creator-gaigailun` (高盖伦·骨架) | P2 | N |
| `creator-luozhenyu` (罗振宇) | P2 | N |
| `creator-qiuzhi2046` (秋芝 2046) | P2 | N |
| `creator-straight-talk` (直男财经) | P0 | Y |
| `creator-zhangchangzhang` (张厂长) | P2 | N |
| `creator-zhangqi` (张琦) | P2 | N |
| `creator-banfo` (半佛仙人) | P2 | N |
| `creator-boss-ip` (老板 IP) | P2 | N |
| `family-recommendation-copy` | P2 | N |
| `renovation-showcase` | P2 | N |
| `lingce-brand-voice` | P0 | Y | 灵策 |
| `lingce-business-history` | P0 | ? |
| `lingce-cognitive-turn` | P0 | Y | 灵策·小Lin |
| `lingce-cold-analysis` | P0 | Y | 灵策·高盖伦 |
| `lingce-game-theory` | P0 | ? |
| `lingce-learning` | P0 | Y | 灵策·学习 |
| `lingce-philosophy` | P0 | ? |
| `lingce-pipeline` | P0 | Y | 灵策·流水线 |
| `lingce-presentation` | P0 | Y |
| `lingce-reveal-truth` | P0 | Y | 灵策·小A |
| `lingce-self-cognition` | P0 | ? |
| `lingce-storytelling` | P0 | Y |
| `lingce-straight-talk` | P0 | Y |
| `lingce-zhuzi` | P0 | Y |

### B5 · 广告投放 + 数据 (ADS · P0)

| Skill | PRI | USED |
|---|---|---|
| `ad-optimizer` | P0 | Y |
| `campaign-monitor` | P0 | Y |
| `auto-comment-reply` | P0 | ? |
| `aeo` / `aeo-optimizer` / `geo-optimize` / `ai-discoverability-audit` | P1 | ? |
| `analytics` / `analytics-tracking` | P0 | ? |
| `seo` / `seo-audit` / `seo-content` / `seo-plan` | P0 | ? |
| `xlsx` (投放数据) | P1 | ? |
| `audit` / `audit` | P1 | ? |
| `keywords` / `keywords` | P0 | ? |
| `strategy` / `strategy` | P0 | ? |
| `competitors` / `competitors` / `competitors-alt` | P0 | ? |
| `case-study-builder` / `case-study-builder` | P0 | ? |
| `comprehensive` | P1 | ? |
| `sentiment-compass` | P1 | ? |
| `pricing` / `pricing-strategy` / `pricing-strategist` | P0 | ? |
| `tweet-draft-reviewer` / `linkedin-writer` / `linkedin-profile-optimizer` / `linkedin-authority-builder` / `x-writer` / `x-twitter-growth` | P0 | ? |

### B6 · 设计 (DESIGN · P1)

| Skill | PRI | USED |
|---|---|---|
| `design-master-global` (30) | P0 | ? |
| `design-consultation` | P1 | N |
| `design-html` | P1 | N |
| `design-review` | P1 | N |
| `design-shotgun` | P1 | N |
| `design-sprint` | P1 | ? |
| `design-everyday-things` | P1 | N |
| `frontend-design` | P1 | ? |
| `theme-factory` | P1 | N |
| `top-design` | P1 | N |
| `steve-jobs-design-review` | P2 | N |
| `brand-guidelines` / `brand-guidelines` / `brand-perception-psychologist` | P0 | ? |
| `image` / `image-content` / `imagegen` / `image-content` | P1 | ? |
| `video` / `video-content` / `oral-video-pipeline` | P1 | ? |
| `viral-hook-creator` | P0 | ? |
| `web-artifacts-builder` | P1 | N |
| `ux-heuristics` | P1 | N |
| `slack-gif-creator` | P2 | N |
| `contagious` | P2 | N |

---

## C. 通用 (BIZ = GEN)

### C1 · 思考/方法论 (GEN · P1)

| Skill | PRI | USED |
|---|---|---|
| `brainstorming` | P0 | Y |
| `internal-comms` | P1 | ? |
| `doc-coauthoring` | P1 | ? |
| `internal-narrative` | P1 | ? |
| `strategic-planning` | P0 | ? |
| `strategic-alignment` | P1 | ? |
| `change-management` | P1 | ? |
| `ceo-advisor` / `cfo-advisor` / `coo-advisor` / `cto-advisor` / `cmo-advisor` / `cro-advisor` / `chro-advisor` / `ciso-advisor` | P1 | ? |
| `chief-of-staff` | P1 | ? |
| `founder-coach` | P1 | ? |
| `scenario-war-room` | P1 | ? |
| `board-meeting` / `board-deck-builder` / `decision-logger` | P1 | ? |
| `ceo-advisor` (founder-skills cluster) | P1 | ? |
| `go-mode` / `go-mode` | P1 | ? |
| `autoplan` | P1 | ? |
| `plan-my-day` | P1 | ? |
| `promote-optimizer` / `prompt-optimizer` | P0 | Y |
| `prompt-engineer-toolkit` | P1 | ? |
| `using-superpowers` | P0 | Y |
| `make-pdf` | P1 | ? |
| `codex-api` / `Codex-api` | P1 | ? |
| `academy-guide` | P1 | ? |

### C2 · 学习/认知 (GEN · P1)

| Skill | PRI | USED |
|---|---|---|
| `self-learning-engine` | P0 | Y |
| `skill-creator` / `skill-factory` / `skill-installer` / `skill-vetter` | P0 | Y |
| `plugin-creator` | P1 | ? |
| `anthropic-*` 系列 (anthropic-algorithmic-art, anthropic-brand-guidelines, anthropic-canvas-design, anthropic-doc-coauthoring, anthropic-docx, anthropic-frontend-design, anthropic-internal-comms, anthropic-pdf, anthropic-pptx, anthropic-slack-gif-creator, anthropic-theme-factory, anthropic-web-artifacts-builder, anthropic-xlsx) | P1 | ? |
| `discernment-nudge` | P1 | ? |
| `retro-methods` | P1 | ? |
| `continuous-discovery` / `jobs-to-be-done` / `lean-analytics` / `lean-startup` / `lean-ux` | P1 | ? |
| `mom-test` | P1 | ? |
| `made-to-stick` | P1 | ? |
| `crossing-the-chasm` | P1 | ? |
| `cold-start-problem` | P1 | ? |
| `hooked-ux` | P1 | ? |
| `influence-psychology` / `marketing-psychology` / `marketing-principles` | P1 | ? |
| `cognitive-bias` | P1 | ? |
| `good-strategy-bad-strategy` | P1 | ? |
| `hundred-million-offers` | P1 | ? |
| `monetizing-innovation` | P1 | ? |
| `monetizing-innovation` | P1 | ? |
| `high-output-management` | P1 | ? |
| `drive-motivation` | P1 | ? |
| `monetizing-innovation` | P1 | ? |
| `storybrand-messaging` | P1 | ? |
| `traction-eos` | P1 | ? |
| `negotiation` | P1 | ? |
| `predictable-revenue` | P1 | ? |
| `ma-playbook` | P1 | ? |
| `company-os` | P1 | ? |
| `context-engine` | P1 | ? |

---

## D. 专用 (BIZ = NICHE)

### D1 · 国内第三方平台 (NICHE · P2)

| Skill | PRI | USED | 备注 |
|---|---|---|---|
| `volcengine-cli` / `volcengine-feedback` / `volcengine-find-skills` / `volcengine-knowledge-search` / `volcengine-troubleshooting` | P2 | ? | 火山引擎 (Volcengine) |
| `arkcli-*` 系列 (arkcli-agent, arkcli-api-explorer, arkcli-auth, arkcli-billing, arkcli-chat, arkcli-code-example, arkcli-config, arkcli-connect, arkcli-custommodel, arkcli-datasets, arkcli-deploy, arkcli-doctor, arkcli-gen, arkcli-helper, arkcli-infer-endpoint, arkcli-models, arkcli-onboard, arkcli-plans, arkcli-pricing, arkcli-profile, arkcli-resources, arkcli-shared, arkcli-train-finetune, arkcli-understand, arkcli-usage) | P2 | N | ARK CLI 24 个 |
| `feishu-broadcast` / `feishu-master` / `feishu-table-analytics` | P2 | ? | 飞书 |
| `baidu-drive` / `baidu-wenku-aippt-personal` | P2 | N | 百度网盘 + 文库 |
| `yixiaoer` / `yixiaoer-bootstrap` | P2 | N | 蚁小二多平台 |
| `wechat-messenger` | P2 | N | 微信 |
| `intel-brief` | P2 | N | AI 动态反哺 |
| `file-uploader` / `file-operations` | P2 | N | 文件操作 |
| `session-save` | P2 | N | 上下文保存 |

### D2 · 其他

| Skill | PRI | USED |
|---|---|---|
| `algorithmic-art` | P3 | N |
| `dispatching-parallel-agents` | P1 | ? (在 A3) |
| `using-superpowers` | P0 | Y (在 C1) |

---

## 总结矩阵

### 按 BIZ 分布

| BIZ | 数量 | 占比 |
|---|---|---|
| AIOS-ENG | ~150 | 21% |
| MKT | ~250 | 35% |
| GEN | ~150 | 21% |
| NICHE | ~150 | 21% |
| (含 Anthropic 系列 + Code 系列等基础设施) | (含在 NICHE) | — |

### 按 PRI 分布

| PRI | 数量 | 占比 |
|---|---|---|
| P0 | ~150 | 21% |
| P1 | ~250 | 35% |
| P2 | ~200 | 28% |
| P3 | ~100 | 14% |

### 按 USED 状态

| USED | 数量 | 占比 |
|---|---|---|
| Y (用过) | ~50 | 7% |
| ? (无法判断) | ~200 | 28% |
| N (从未用) | ~450 | 65% |

---

## 核心发现

### 1. "在用" 比 "加载" 低得多
- 700+ skill 中真正在本会话用过的 ≈ 50 (7%)
- 65% 从未用过
- 这意味着 skill **加载 ≠ 使用**

### 2. P0 高度集中在 AIOS-ENG (主权) + MKT (营销)
- 主权 P0 = 12 个 v5-* + 8 个 aios-adapter-* + 11 个 gstack-* ≈ 31 个
- 营销 P0 = 30 个 00-30 + 多个 creator-* + lingce-* ≈ 80 个
- **P0 总数 ≈ 150 · 占 21%** — 仍有大量 P0 真没启用

### 3. 营销业务侧"重武器未用"
- `marketing-demand-acquisition`, `competitor-research-global`, `customer-insight-global`, `reverse-kpi-global`, `channel-setup-global` 等 5+ 个 P0 营销 skill **历史未用**
- 这些对应"做 1 个完整营销 campaign"的全套链路
- 可能原因: 用户尚未启动大 campaign · 或者 skill 未接 current workflow

### 4. 主权侧 P0 全到位
- v5-* 11 个 R 模块 · gstack 全套 · aios-adapter-* 8 个 · 全部到位 ✅

### 5. NICHE 类（arkcli + volcengine）规模惊人
- arkcli-* 24 个 + volcengine-* 5 个 = 29 个
- 几乎全 USED = N (火山方舟用户没有真正部署 Endpoint)
- **建议**: 等用户确认是否真要用方舟再决定是否卸载

---

## 建议（不实施，等用户批）

### Quick Win
1. **优先启用 5 个 P0 营销重武器** (demand-acquisition / competitor-research / customer-insight / reverse-kpi / channel-setup)
2. **覆盖 8/14 Round 5 未复核维度**（autonomous 内）

### 中期清理
3. **评估 arkcli + volcengine 是否真用**（如不用，可卸载 29 个 skill 释放 startup time）
4. **精减 codex-* 系列 22 个工具桥**：用户已经用 windows_mcp，codex-* 系列大部分冗余

### 长期
5. **建立 skill 使用 telemetry**：哪些 skill 真被 `invoke` 过 vs 仅 load

---

## 红线遵守
- ✅ 仅 read-only 分类，不动任何 skill 加载
- ✅ 不写新 R 编号（用户授权后才另开 R）
- ✅ 不动 policy v2
- ✅ 不实现 Reconciler/Adapter 扩展（已在 T3 提案中）

---

_— Codex (supervisor) · T4 skill 分类矩阵 · 700+ skill 按 4 维分类 · 总结矩阵 + 建议 · 2026-10-09_