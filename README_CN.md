# AIOS Kernel (中文版)

> **生产就绪的 Python 任务调度框架** · R1505-4 · 78+ commits
> 完整英文文档看 [README.md](README.md) · [CHANGELOG.md](CHANGELOG.md) 看历史

---

## 简介

AIOS Kernel 是 macxiaxia-boop 项目的 Python 核心包。它实现了**多 Agent 协同的任务调度器**，用于 AIOS VNext Phase A 程序。

简单说，它干这几件事：
1. 接收任务（通过 HTTP 或 MCP）
2. 按优先级排队（P0 > P1 > P2）
3. 分发给 4 个 Agent Worker 之一（claude-code / codex / openclaw / hermes）
4. 处理重试 / 熔断 / 死信队列
6. 提供 Prometheus metrics 给生产监控

---

## 快速开始

### 1. 安装

```bash
cd D:/AIOS/kernel
pip install -e ".[dev]"
```

### 2. 启动 scheduler（前台模式）

```bash
.venv/Scripts/python.exe -m aios_kernel.cli scheduler run
# 或 POSIX:
python -m aios_kernel.cli scheduler run
```

会看到类似输出：
```
[scheduler] starting dispatcher + health tasks spawned
[scheduler.dispatcher] loop started
```

按 Ctrl+C 停止。

### 3. 验证运行

```bash
curl http://localhost:9000/health
# {"ok": true, "service": "aios-gateway", "version": "R1503"}

bash start-prod.sh status
# /health -> 200
# /healthz -> 200
# /readyz -> 200
# /metrics -> 200
```

### 4. 提交任务

```bash
curl -X POST http://localhost:9000/tasks \
  -H "Content-Type: application/json" \
  -d '{"goal_id": "g1", "title": "我的第一个任务", "priority": "P1"}'
# → 202 {"run_id": "run-...", "task_id": "..."}
```

### 5. 跑测试

```bash
.venv/Scripts/python.exe -m pytest tests/ -v
# 78 unit + 4 audit + 9 e2e + 4 observability + 4 auth + 2 openapi = 116+ PASS
```

---

## 部署到生产

### Docker Compose（推荐）

```bash
# 1. 设置密码
export AIOS_DB_PASSWORD="$(openssl rand -hex 32)"

# 2. 启动
docker compose build
docker compose up -d

# 3. 验证
docker compose ps
curl http://localhost:9000/healthz
curl http://localhost:9000/metrics
```

### Systemd

```bash
sudo cp deploy/aios-kernel.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now aios-kernel
sudo systemctl status aios-kernel
journalctl -u aios-kernel -f
```

### 一键启动脚本

```bash
bash start-prod.sh status    # 健康检查
bash start-prod.sh metrics   # Prometheus 指标
bash start-prod.sh run       # 前台运行
bash start-prod.sh background # 后台 daemon
bash start-prod.sh test      # 跑测试
bash start-prod.sh stop       # 停止 daemon
bash start-prod.sh tail       # tail 日志
```

### 部署前自检

```bash
bash deploy/deploy-validate.sh
# ✓ Python 版本 OK
# ✓ aios_kernel 已安装
# ✓ 测试 PASS
# ✓ 数据库可达
# ✓ 端口空闲
# ...
```

---

## 4 个 Agent

| 模块 | 默认 provider | 默认端口 | 状态 |
|---|---|---|---|
| `claude-code-adapter` | MiniMax-M3 (VSCode extension) | - | ✅ 真跑 binary |
| `codex-adapter` | gpt-5.1 Codex (OAuth) | - | ✅ 调 codex exec |
| `openclaw-adapter` | lingceAI / multi-provider | :18792 (daemon) | ✅ HTTP POST |
| `hermes-adapter` | in-process CIO | - | ✅ in-proc |

---

## API 速查

| Method | Path | 用途 | Code |
|---|---|---|---|
| GET | `/health` | JSON 状态 | 200 |
| GET | `/healthz` | K8s liveness | 200 |
| GET | `/readyz` | K8s readiness | 200 |
| GET | `/metrics` | Prometheus | 200 |
| POST | `/tasks` | 提交任务 | 202 / 422 |
| GET | `/tasks/{id}` | 查询状态 | 200 |
| GET | `/openapi.json` | OpenAPI schema | 200 |
| GET | `/docs` | Swagger UI | 200 |
| POST | `/mcp` | JSON-RPC MCP | 200 |

### `POST /tasks` 请求

```json
{
  "goal_id": "string (required)",
  "title": "string (required, max 200)",
  "description": "string (optional)",
  "priority": "P0 | P1 | P2 (default P2)"
}
```

完整文档：[docs/API_REFERENCE.md](docs/API_REFERENCE.md)

---

## 监控

### Prometheus

```promql
# 任务提交率
rate(aios_kernel_submitted_total[5m])

# 任务失败率
rate(aios_kernel_failed_total[5m]) / rate(aios_kernel_submitted_total[5m])

# DLQ 大小
aios_kernel_dlq_size

# 平均调度延迟
aios_kernel_avg_dispatch_latency_seconds

# 熔断器打开次数（worker 健康）
rate(aios_kernel_circuit_opened_total[1h])
```

### Grafana dashboard 建议

- `/healthz` 1xx 表示进程正常
- `/readyz` 5xx 表示子系统异常
- `aios_kernel_dlq_size > 100` 表示 worker 长期故障
- `rate(aios_kernel_failed_total[5m]) > 0.1` 表示任务失败率超 10%

---

## 安全

### 鉴权（生产必须开）

```bash
export AIOS_KERNEL_AUTH_REQUIRED=1
export AIOS_KERNEL_JWT_SECRET="$(openssl rand -hex 32)"
# 现在 /tasks 需要 Bearer token
```

生成 token：
```python
from aios_kernel.gateway.auth import sign_jwt
print(sign_jwt({"sub": "client-id"}, secret=b"your-secret"))
```

### 限流

```bash
export AIOS_KERNEL_RATELIMIT_ENABLED=1
# 每个 worker-id 100 token 桶 / 10 token/s
```

---

## 配置（环境变量）

| 变量 | 默认 | 说明 |
|---|---|---|
| `AIOS_KERNEL_PORT` | 9000 | HTTP gateway 端口 |
| `AIOS_KERNEL_AUTH_REQUIRED` | 0 | 是否要 JWT |
| `AIOS_KERNEL_RATELIMIT_ENABLED` | 0 | 是否限流 |
| `AIOS_KERNEL_JWT_SECRET` | - | JWT 密钥(32+ chars, auth enabled 时必须) |
| `AIOS_KERNEL_DATABASE_URL` | - | PostgreSQL DSN (生产必填) |
| `AIOS_KERNEL_OFFLINE` | 1 | 禁用外部 API (生产) |
| `AIOS_LOG_LEVEL` | INFO | DEBUG / INFO / WARNING |
| `AIOS_INSTANCE_ID` | aios-kernel-1 | 用于 metrics label |

---

## 故障排查

### Scheduler 没启动

```bash
bash start-prod.sh status    # 检查 health
python -m aios_kernel.cli scheduler status
journalctl -u aios-kernel -n 50
```

### 任务不处理

```bash
# 看 metrics
curl http://localhost:9000/metrics | grep aios_kernel

# DLQ 增长 → worker 失败
curl http://localhost:9000/metrics | grep dlq

# 重启 scheduler
sudo systemctl restart aios-kernel
```

### Token 过期

```bash
# 401 → JWT 过期。生成新 token:
python -c "from aios_kernel.gateway.auth import sign_jwt; print(sign_jwt({'sub':'worker'}, secret=b'YOUR_SECRET'))"
```

---

## 仓库结构

```
src/aios_kernel/
  scheduler.py         (R1503-001)  任务调度器
  state_machine.py     (R1503-002)  状态机
  workers/adapters.py  (R1503-003)  4 Agent 注册
  agents/              (R1503-004/005)  协议 + 注册表
  gateway/             (R1503-007/008/009)  HTTP + MCP + JWT + 限流
  runtime/             (R1503-010/011/012)  进程 + 内存 + Cron
  cli.py               (CLI)

tests/
  unit/                (78 + 4 audit = 82 tests)
  integration/         (9 e2e + 4 obs + 4 auth + 2 openapi = 19 tests)

docs/
  architecture.md
  acceptance_criteria.md
  API_REFERENCE.md

deploy/
  aios-kernel.service
  aios-kernel.supervisord.conf
  aios-kernel.service.override.md
  deploy-validate.sh

.github/workflows/
  aios-kernel-ci.yml
  coverage-badge.yml
```

---

## 进一步

- **完整英文 README**: [README.md](README.md)
- **API 文档**: [docs/API_REFERENCE.md](docs/API_REFERENCE.md)
- **架构**: [docs/architecture.md](docs/architecture.md)
- **变更日志**: [CHANGELOG.md](CHANGELOG.md) / [CHANGELOG_CN.md](CHANGELOG_CN.md)

---

*Generated by R1505-5 · Claude Code (MiniMax-M3) · 2026-10-12*
*Co-Authored-By: Claude Code <noreply@anthropic.com>*