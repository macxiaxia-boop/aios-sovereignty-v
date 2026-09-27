# AIOS Capability Radar · R212 · 2026-09-26

**spec#11 Tier A-F 多源搜索 · spec#43 互联网能力更新机制 · spec#45 Technology Watchlist**

## Tier A - 官方来源
- OpenAI Codex (docs blog GitHub changelog)
- Anthropic Claude Code (docs blog GitHub) - https://code.claude.com/docs/en/hooks
- Nous Research Hermes (hermes-agent.nousresearch.com PyPI)
- OpenClaw Official (openclaw.ai docs GitHub org)
- MiniMax Anthropic 官方

## Tier B - 开源社区
- GitHub (anthropics NousResearch openclaw swarmclawai gregorizeidler 6missedcalls etc)
- PyPI (hermes-agent)
- npm (swarmclaw 5 marketplace 插件)
- HuggingFace (Hermes 4 模型待定位)
- Docker Hub
- MCP Registry (https://mcp.so 待 research)

## Tier C - 技术社区
- Hacker News Reddit X Discord DEV
- (尚未系统化 下一步 STEP 13)

## Tier D - 产品发现
- Product Hunt AlternativeTo AI product directories
- (尚未系统化)

## Tier E - 内容平台
- YouTube Bilibili 技术博客
- (尚未系统化)

## Tier F - 新闻
- 因为新发布产品可能没 GitHub 必须新闻搜索
- (尚未系统化)

---

## 当前 Watchlist (15 实体)
1. Codex CLI · active
2. Claude Code · active · 5 plugins installed
3. Hermes Agent · active v0.21.3 · update blocked (R211)
4. OpenClaw Gateway · active
5. Muse AI · unknown (R211)
6. SwarmClaw · failed install (R211)
7. GoClaw · rejected (与 OpenClaw 重叠)
8. PicoClaw · rejected (非用户场景)
9. NanoBot · candidate
10. IronClaw · candidate
11. Anthropic Marketplace · 314 plugins · 5 installed
12. FFmpeg Wizard · candidate_priority_P1 (R212 新发现)
13. Cut/Storm · candidate
14. video-editing-skill · candidate_high_composability (R212 新发现)
15. mcp-video-editor · candidate_MCP

---

## 已提取的 Mechanism (13)
- Claude Code context steering · hooks (18+ events) · marketplace
- Claude Code hook permission decision (2026) - exit code 2 + hookSpecificOutput.permissionDecision
- Hermes self-learning · subagent isolation · cron delivery
- Codex repo execution · OpenClaw multi-channel
- SwarmClaw org chart · Muse UX (待研究)
- FFmpeg Wizard canonical pipeline (Whisper + GPT-4 + MoviePy + FFmpeg RE-ENCODE)
- video-editing-skill pure Bash FFmpeg Whisper AI-agent-ready

## Canonical Video Pipeline (R212 from WebSearch)
```
Raw Video
 ↓
ffmpeg extract audio
   ↓
Whisper timestamped transcript JSON SRT
   ↓
LLM (GPT-4) identify cuts fillers dead air false starts mistakes
   ↓
FFmpeg RE-ENCODE libx264 crf 18-20 cut concatenate (NEVER -c copy)
   ↓
FFmpeg burn SRT subtitles
   ↓
Optional B-Roll insertion color correction music zoom
   ↓
Final MP4 optimized for platform
```

CRF settings: 15-17 archive · 18-20 YouTube · 21-23 social

## 下一步
1. STEP 13b: Multi-tier WebSearch (Tier C D E F)
2. STEP 14: Video pipeline sandbox (ffmpeg + whisper + pyscenedetect + auto-editor)
3. STEP 15: Content pipeline design (spec#17)
4. STEP 16: 12 Acceptance Tests (spec#82)
5. STEP 17: Repair br-aios-hermes (PATH conflict)
