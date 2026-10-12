"""agents/protocol.py - MultiAgent Communication Protocol (R1503-004).

Provides AgentMessage dataclass + AgentProtocol class with in-memory transport
for Phase A. Phase B can swap to gRPC / NATS / Redis pubsub.

R1503-004 acceptance:
  - AgentMessage dataclass
  - AgentProtocol: send/receive/broadcast async API
  - in-memory transport (Phase A)
  - Tests >= 80% coverage

Co-Authored-By: Claude Code (Agent 2 / Codex) via AIOS R1503
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

log = logging.getLogger("aios_kernel.agents.protocol")


class MessageType(str, Enum):
    REQUEST = "request"
    RESPONSE = "response"
    EVENT = "event"
    BROADCAST = "broadcast"


@dataclass
class AgentMessage:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    recipient: str = ""  # "*" for broadcast
    type: MessageType = MessageType.REQUEST
    payload: dict = field(default_factory=dict)
    ts: float = field(default_factory=time.time)
    correlation_id: str | None = None  # for REQUEST->RESPONSE


@dataclass
class AgentRegistration:
    name: str
    capabilities: list[str] = field(default_factory=list)
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)


class AgentProtocol:
    """In-memory multi-agent communication protocol (Phase A)."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentRegistration] = {}
        self._handlers: dict[str, Callable[[AgentMessage], Awaitable[None]]] = {}
        self._delivered: list[AgentMessage] = []  # for audit

    # ----- registration ------------------------------------------------

    def register(
        self,
        name: str,
        *,
        capabilities: list[str] | None = None,
        on_message: Callable[[AgentMessage], Awaitable[None]] | None = None,
    ) -> AgentRegistration:
        if name in self._agents:
            raise ValueError(f"agent {name!r} already registered")
        reg = AgentRegistration(name=name, capabilities=capabilities or [])
        self._agents[name] = reg
        if on_message is not None:
            self._handlers[name] = on_message
        return reg

    def unregister(self, name: str) -> None:
        self._agents.pop(name, None)
        self._handlers.pop(name, None)

    def list(self) -> list[str]:
        return list(self._agents.keys())

    def has(self, name: str) -> bool:
        return name in self._agents

    def capabilities_of(self, name: str) -> list[str]:
        if name not in self._agents:
            raise KeyError(f"agent {name!r} not registered")
        return list(self._agents[name].capabilities)

    # ----- messaging ---------------------------------------------------

    async def send(self, msg: AgentMessage) -> None:
        if msg.recipient not in self._agents:
            raise KeyError(f"recipient {msg.recipient!r} not registered")
        await self._agents[msg.recipient].queue.put(msg)
        self._delivered.append(msg)
        log.info("agent_protocol.send: %s -> %s type=%s", msg.sender, msg.recipient, msg.type.value)

    async def receive(self, agent_name: str, *, timeout_s: float = 1.0) -> AgentMessage | None:
        if agent_name not in self._agents:
            raise KeyError(f"agent {agent_name!r} not registered")
        try:
            return await asyncio.wait_for(
                self._agents[agent_name].queue.get(), timeout=timeout_s
            )
        except TimeoutError:
            return None

    async def broadcast(self, msg: AgentMessage) -> None:
        """Send to all registered agents (recipient becomes '*')."""
        msg = AgentMessage(
            id=msg.id,
            sender=msg.sender,
            recipient="*",
            type=MessageType.BROADCAST,
            payload=msg.payload,
            ts=msg.ts,
            correlation_id=msg.correlation_id,
        )
        for name in list(self._agents.keys()):
            msg_one = AgentMessage(
                id=msg.id,
                sender=msg.sender,
                recipient=name,
                type=MessageType.BROADCAST,
                payload=msg.payload,
                ts=msg.ts,
                correlation_id=msg.correlation_id,
            )
            await self._agents[name].queue.put(msg_one)
        self._delivered.append(msg)
        log.info("agent_protocol.broadcast: %s -> %d agents", msg.sender, len(self._agents))

    # ----- request/response ------------------------------------------

    async def request(
        self,
        sender: str,
        recipient: str,
        payload: dict,
        *,
        timeout_s: float = 5.0,
    ) -> AgentMessage | None:
        cid = str(uuid.uuid4())
        req = AgentMessage(
            sender=sender, recipient=recipient,
            type=MessageType.REQUEST, payload=payload, correlation_id=cid,
        )
        await self.send(req)
        # wait for response with matching correlation_id
        deadline_ts = time.time() + timeout_s
        while time.time() < deadline_ts:
            remaining = max(0.01, deadline_ts - time.time())
            resp = await self.receive(sender, timeout_s=remaining)
            if resp is None:
                return None
            if resp.correlation_id == cid and resp.sender == recipient:
                return resp
        return None

    async def respond(
        self, original: AgentMessage, payload: dict
    ) -> None:
        """Send a response back to the original requester."""
        assert original.correlation_id is not None
        resp = AgentMessage(
            sender=original.recipient,
            recipient=original.sender,
            type=MessageType.RESPONSE,
            payload=payload,
            correlation_id=original.correlation_id,
        )
        await self.send(resp)

    # ----- audit ------------------------------------------------------

    @property
    def delivered(self) -> list[AgentMessage]:
        return list(self._delivered)


__all__ = ["AgentMessage", "AgentProtocol", "AgentRegistration", "MessageType"]