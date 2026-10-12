"""test_adapters.py - Unit tests for adapters framework (R1503-003)."""
from __future__ import annotations

import pytest

from aios_kernel.workers.adapters import (
    SubprocessRunner,
    _render_arg_template,
    cli_subprocess_adapter,
    http_adapter,
)
from aios_kernel.workers.registry import WorkerRegistry


def test_render_arg_template_simple():
    out = _render_arg_template(
        "run {task_id} {task_title}",
        {"task_id": "abc", "task_title": "hello"},
    )
    assert out == "run abc hello"


def test_render_arg_template_missing_key_raises():
    with pytest.raises(ValueError):
        _render_arg_template("{nonexistent}", {})


@pytest.mark.asyncio
async def test_subprocess_runner_runs_command():
    runner = SubprocessRunner()
    stdout, stderr, code = await runner.run(
        ["python", "-c", "print('hi')"], env={},
    )
    assert code == 0
    assert stdout.strip() == "hi"
    assert stderr == ""


@pytest.mark.asyncio
async def test_cli_adapter_health():
    adapter = cli_subprocess_adapter(
        "test-cli", binary="python", arg_template="",
    )
    h = await adapter.health()
    assert h.worker_id == "test-cli"
    assert h.status.value == "healthy"


@pytest.mark.asyncio
async def test_cli_adapter_execute_happy():
    adapter = cli_subprocess_adapter(
        "test-cli", binary="python", arg_template="-c print(1)", timeout_s=5.0,
    )
    from aios_kernel.domain.task import Task, TaskType
    task = Task(
        id="11111111-1111-1111-1111-111111111111",
        goal_id="g",
        title="x",
        task_type=TaskType.CUSTOM,
    )
    art = await adapter.execute(task)
    assert art.task_id == task.id
    assert art.inline_json["exit_code"] == 0
    assert art.inline_json["healthy"] is True


@pytest.mark.asyncio
async def test_cli_adapter_execute_nonzero():
    adapter = cli_subprocess_adapter(
        "test-cli-fail", binary="python", arg_template="-c exit(2)", timeout_s=5.0,
    )
    from aios_kernel.domain.task import Task, TaskType
    task = Task(
        id="22222222-2222-2222-2222-222222222222",
        goal_id="g",
        title="y",
        task_type=TaskType.CUSTOM,
    )
    art = await adapter.execute(task)
    assert art.inline_json["exit_code"] == 2
    assert art.inline_json["healthy"] is False


@pytest.mark.asyncio
async def test_http_adapter_health():
    adapter = http_adapter("test-http", base_url="http://localhost:9999")
    h = await adapter.health()
    assert h.worker_id == "test-http"
    assert h.status.value == "healthy"


@pytest.mark.asyncio
async def test_http_adapter_execute_stub():
    adapter = http_adapter("test-http", base_url="http://localhost:9999")
    from aios_kernel.domain.task import Task, TaskType
    task = Task(
        id="33333333-3333-3333-3333-333333333333",
        goal_id="g",
        title="z",
        task_type=TaskType.CUSTOM,
    )
    art = await adapter.execute(task)
    assert art.inline_json["stub"] is True
    assert art.inline_json["worker"] == "test-http"


def test_register_four_agent_team_is_idempotent():
    from aios_kernel.workers.adapters import register_four_agent_team

    registry = WorkerRegistry()
    register_four_agent_team(registry)
    n_first = len(registry.list_ids())
    assert n_first >= 1  # at least one
    register_four_agent_team(registry)  # idempotent
    n_second = len(registry.list_ids())
    assert n_first == n_second
