#!/usr/bin/env bash
# start-aios-kernel.sh - R1503-FINAL 一键启动 AIOS kernel 4-Agent scheduler
#
# 用法:
#   bash start-aios-kernel.sh             # 启动 scheduler (前台)
#   bash start-aios-kernel.sh status      # 状态快照
#   bash start-aios-kernel.sh test        # 跑测试
#   bash start-aios-kernel.sh curl        # 测试 HTTP gateway
#   bash start-aios-kernel.sh mcp         # 测试 MCP gateway
#
# Co-Authored-By: Claude Code via AIOS R1503-FINAL

set -euo pipefail

cd "$(dirname "$0")"

# 找 Python (Win + POSIX)
if [[ -f ".venv/Scripts/python.exe" ]]; then
    PYTHON=".venv/Scripts/python.exe"
elif [[ -f ".venv/bin/python" ]]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python"
fi

action="${1:-run}"

case "$action" in
    run)
        echo "[aios-kernel] starting 4-Agent scheduler (foreground, Ctrl-C to stop)..."
        exec "$PYTHON" -m aios_kernel.cli scheduler run
        ;;
    status)
        exec "$PYTHON" -m aios_kernel.cli scheduler status
        ;;
    test)
        echo "[aios-kernel] running 91 R1503 tests..."
        exec "$PYTHON" -m pytest \
            tests/unit/test_scheduler.py \
            tests/unit/test_state_machine.py \
            tests/unit/test_adapters.py \
            tests/unit/test_agents.py \
            tests/unit/test_gateway.py \
            tests/unit/test_runtime.py \
            tests/unit/test_scheduler_audit.py \
            tests/integration/ \
            -v
        ;;
    curl)
        # 启动 daemon in background, 测试 /tasks endpoint, 然后停
        echo "[aios-kernel] starting daemon in background for HTTP test..."
        "$PYTHON" -m aios_kernel.cli scheduler run &
        SCHED_PID=$!
        sleep 3
        echo "[aios-kernel] POST /tasks ..."
        # import fastapi + uvicorn
        # spawn uvicorn server in background
        cat > /tmp/_test_server.py <<EOF
import uvicorn
from aios_kernel.gateway.http import create_app
from aios_kernel.scheduler import AIOSScheduler, SchedulerConfig
from aios_kernel.workers.adapters import register_four_agent_team
from aios_kernel.workers.registry import WorkerRegistry

reg = WorkerRegistry()
register_four_agent_team(reg)
sched = AIOSScheduler(registry=reg, config=SchedulerConfig(max_concurrent=2))
app = create_app(sched)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8088, log_level="warning")
EOF
        "$PYTHON" /tmp/_test_server.py &
        UV_PID=$!
        sleep 5

        echo "  -> /health:"
        curl -s http://127.0.0.1:8088/health
        echo ""

        echo "  -> POST /tasks:"
        curl -s -X POST http://127.0.0.1:8088/tasks \
            -H "Content-Type: application/json" \
            -d '{"goal_id": "g-shell", "title": "via-curl", "priority": "P1"}'
        echo ""

        kill $UV_PID 2>/dev/null || true
        kill $SCHED_PID 2>/dev/null || true
        echo "[aios-kernel] test done"
        ;;
    mcp)
        echo "[aios-kernel] MCP JSON-RPC test..."
        "$PYTHON" -c "
import json
from aios_kernel.gateway.mcp import MCPServer
from aios_kernel.scheduler import AIOSScheduler, SchedulerConfig
from aios_kernel.workers.adapters import register_four_agent_team
from aios_kernel.workers.registry import WorkerRegistry
import asyncio

reg = WorkerRegistry()
register_four_agent_team(reg)
sched = AIOSScheduler(registry=reg, config=SchedulerConfig(max_concurrent=2))
srv = MCPServer(sched)

async def main():
    print('--- initialize ---')
    print(json.dumps(srv.handle_initialize({}), indent=2))
    print('--- tools/list ---')
    res = srv.handle_tools_list()
    print(f'  {len(res[\"tools\"])} tools registered')
    print('--- tools/call aios_get_health ---')
    r = await srv.handle_tools_call('aios_get_health', {})
    print(json.dumps(r, indent=2))

asyncio.run(main())
"
        ;;
    *)
        echo "Usage: $0 {run|status|test|curl|mcp}"
        exit 1
        ;;
esac