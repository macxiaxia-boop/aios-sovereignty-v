"""test_agents.py - Tests for agents/protocol + agents/registry (R1503-004/005)."""
from __future__ import annotations

import asyncio

import pytest

from aios_kernel.agents.protocol import (
    AgentMessage,
    AgentProtocol,
    MessageType,
)
from aios_kernel.agents.registry import AgentRegistry

# ----- protocol -----------------------------------------------------------


@pytest.mark.asyncio
async def test_protocol_register_and_send():
    p = AgentProtocol()
    p.register("alice", capabilities=["chat"])
    msg = AgentMessage(sender="alice", recipient="alice", type=MessageType.EVENT)
    await p.send(msg)
    got = await p.receive("alice")
    assert got is not None
    assert got.sender == "alice"


@pytest.mark.asyncio
async def test_protocol_send_to_unknown_raises():
    p = AgentProtocol()
    with pytest.raises(KeyError):
        await p.send(AgentMessage(sender="a", recipient="nope"))


@pytest.mark.asyncio
async def test_protocol_broadcast():
    p = AgentProtocol()
    p.register("a")
    p.register("b")
    p.register("c")
    await p.broadcast(AgentMessage(sender="a", recipient="*", payload={"v": 1}))
    for n in ("a", "b", "c"):
        m = await p.receive(n)
        assert m is not None
        assert m.payload == {"v": 1}


@pytest.mark.asyncio
async def test_protocol_request_response():
    p = AgentProtocol()
    p.register("client")
    p.register("server")

    async def server_handler():
        msg = await p.receive("server", timeout_s=1.0)
        await p.respond(msg, payload={"echo": msg.payload})

    asyncio.create_task(server_handler())
    resp = await p.request("client", "server", payload={"q": "hi"}, timeout_s=2.0)
    assert resp is not None
    assert resp.payload == {"echo": {"q": "hi"}}


@pytest.mark.asyncio
async def test_protocol_receive_timeout():
    p = AgentProtocol()
    p.register("x")
    msg = await p.receive("x", timeout_s=0.05)
    assert msg is None


# ----- registry -----------------------------------------------------------


def test_registry_register_and_get():
    r = AgentRegistry()
    r.register("a", capabilities=["chat", "code"])
    assert r.has_capability("a", "chat")
    assert not r.has_capability("a", "video")


def test_registry_register_duplicate_raises():
    r = AgentRegistry()
    r.register("a")
    with pytest.raises(ValueError):
        r.register("a")


def test_registry_unregister():
    r = AgentRegistry()
    r.register("a")
    r.unregister("a")
    assert r.list_names() == []


def test_registry_add_remove_capability():
    r = AgentRegistry()
    r.register("a")
    r.add_capability("a", "x")
    assert r.has_capability("a", "x")
    r.remove_capability("a", "x")
    assert not r.has_capability("a", "x")


def test_registry_find_by_capability_priority():
    r = AgentRegistry()
    r.register("a", capabilities=["x"], priority=100)
    r.register("b", capabilities=["x", "y"], priority=10)  # higher prio
    r.register("c", capabilities=["x"], priority=50)
    matches = r.find_by_capability("x")
    assert [m.name for m in matches] == ["b", "c", "a"]


def test_registry_find_best():
    r = AgentRegistry()
    r.register("a", capabilities=["x"], priority=100)
    r.register("b", capabilities=["x"], priority=10)
    assert r.best_match("x").name == "b"


def test_registry_health_excludes_unhealthy():
    r = AgentRegistry()
    r.register("a", capabilities=["x"], priority=10)
    r.register("b", capabilities=["x"], priority=100)
    r.set_healthy("a", False)
    matches = r.find_by_capability("x")
    assert [m.name for m in matches] == ["b"]


def test_registry_advertise_all():
    r = AgentRegistry()
    r.register("a", capabilities=["x", "y"])
    r.register("b", capabilities=["x"])
    ad = r.advertise_all()
    assert ad["a"] == {"x", "y"}
    assert ad["b"] == {"x"}


def test_registry_get_unknown_raises():
    r = AgentRegistry()
    with pytest.raises(KeyError):
        r.get("nope")
