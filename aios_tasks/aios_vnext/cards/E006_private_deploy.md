---
id: E006
title: Private Deployment (Docker + airgap)
owner: CC
priority: P0
track: 7 — VNext Phase E (CloudTech)
preconditions: [E002]
estimated_minutes: 60
depends_on: [E002]
blocks: [E007]
status: Pending
created: 2026-10-08
---

## Scope
1. Dockerfile (Python 3.11 + kernel)
2. docker-compose.yml (PG + AIOS kernel + verifier + sidecar)
3. airgap 配置 (no external API, all offline)
4. 集成测试 (5 case: dockerfile_syntax, compose_valid, airgap_check, no_external_apis, single_binary)
