"""gateway/mcp.py - MCP Server surface for AIOSScheduler (R1503-008).

JSON-RPC 2.0 / Model Context Protocol surface. Exposes tools/list and
tools/call so an MCP client (Codex / Hermes / OpenClaw) can submit tasks.

R1503-008 acceptance:
  - handle_initialize() returns server info
  - handle_tools_list() returns registered tools (submit_task, get_metrics, get_health)
  - handle_tools_call(name, args) dispatches
  - Tests >= 80% coverage

Co-Authored-By: Claude Code (Agent 3 / OpenClaw) via AIOS R1503
"""
from __future__ import annotations

import logging
from typing import Any

from aios_kernel.scheduler import AIOSScheduler

log = logging.getLogger("aios_kernel.gateway.mcp")


# Tool definitions (MCP "tools/list")
TOOLS: list[dict[str, Any]] = [
    {
        "name": "aios_submit_task",
        "description": "Submit a task to the AIOSScheduler. Returns run_id and task_id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "goal_id": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "priority": {"type": "string", "enum": ["P0", "P1", "P2"], "default": "P2"},
            },
            "required": ["goal_id", "title"],
        },
    },
    {
        "name": "aios_get_task_status",
        "description": "Query the status of a task by run_id.",
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
    },
    {
        "name": "aios_get_metrics",
        "description": "Return scheduler metrics snapshot.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "aios_get_health",
        "description": "Health check endpoint.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


class MCPServer:
    """Minimal MCP server (tools/list + tools/call)."""

    def __init__(self, scheduler: AIOSScheduler) -> None:
        self._scheduler = scheduler

    # ---- protocol methods ------------------------------------------

    def handle_initialize(self, _params: dict) -> dict:
        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "aios-mcp", "version": "R1503-008"},
            "capabilities": {"tools": {}},
        }

    def handle_tools_list(self) -> dict:
        return {"tools": TOOLS}

    async def handle_tools_call(self, name: str, arguments: dict) -> dict:
        if name == "aios_get_health":
            return {"content": [{"type": "text", "text": "ok"}]}
        if name == "aios_get_metrics":
            return {
                "content": [
                    {"type": "text", "text": str(self._scheduler.metrics())},
                ]
            }
        if name == "aios_get_task_status":
            run_id = arguments.get("run_id")
            if not run_id:
                return {
                    "isError": True,
                    "content": [{"type": "text", "text": "missing run_id"}],
                }
            st = await self._scheduler.status(run_id)
            return {"content": [{"type": "text", "text": str(st)}]}
        if name == "aios_submit_task":
            from aios_kernel.domain.task import Task, TaskType
            from aios_kernel.scheduler import Priority
            try:
                priority = Priority(arguments.get("priority", "P2"))
            except ValueError:
                return {
                    "isError": True,
                    "content": [
                        {"type": "text", "text": "unknown priority"},
                    ],
                }
            task = Task(
                goal_id=arguments["goal_id"],
                title=arguments["title"],
                description=arguments.get("description"),
                task_type=TaskType.CUSTOM,
            )
            run_id = await self._scheduler.submit(task, priority=priority)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"submitted: run_id={run_id} task_id={task.id}",
                    },
                ]
            }
        return {
            "isError": True,
            "content": [{"type": "text", "text": f"unknown tool {name!r}"}],
        }

    # ---- entry point ------------------------------------------------

    async def handle_request(self, req: dict) -> dict:
        method = req.get("method", "")
        req_id = req.get("id")
        params = req.get("params") or {}
        if method == "initialize":
            result = self.handle_initialize(params)
        elif method == "tools/list":
            result = self.handle_tools_list()
        elif method == "tools/call":
            name = params.get("name", "")
            arguments = params.get("arguments", {})
            result = await self.handle_tools_call(name, arguments)
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"method not found: {method!r}"},
            }
        return {"jsonrpc": "2.0", "id": req_id, "result": result}


__all__ = ["MCPServer", "TOOLS"]
