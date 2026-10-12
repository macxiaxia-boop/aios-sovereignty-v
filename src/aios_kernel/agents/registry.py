"""agents/registry.py - Agent Registry + Capability Negotiation (R1503-005).

Provides:
  - AgentRegistry: track which agents exist + their metadata
  - Capability negotiation: agents advertise capabilities, others query
  - Discovery: find best agent for a capability

R1503-005 acceptance:
  - AgentRegistry API
  - Capability advertise / query
  - Discovery: best-match-by-priority
  - Tests >= 80% coverage

Co-Authored-By: Claude Code (Agent 2 / Codex) via AIOS R1503
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field


@dataclass
class AgentMetadata:
    name: str
    capabilities: set[str] = field(default_factory=set)
    priority: int = 100  # lower = higher priority (used as tiebreaker)
    healthy: bool = True
    metadata: dict = field(default_factory=dict)


class AgentRegistry:
    """Track agents + their capabilities; support discovery by capability."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentMetadata] = {}

    # ----- registration ----------------------------------------------

    def register(
        self,
        name: str,
        *,
        capabilities: Iterable[str] = (),
        priority: int = 100,
        metadata: dict | None = None,
    ) -> AgentMetadata:
        if name in self._agents:
            raise ValueError(f"agent {name!r} already registered")
        meta = AgentMetadata(
            name=name,
            capabilities=set(capabilities),
            priority=priority,
            metadata=dict(metadata or {}),
        )
        self._agents[name] = meta
        return meta

    def unregister(self, name: str) -> None:
        self._agents.pop(name, None)

    def get(self, name: str) -> AgentMetadata:
        if name not in self._agents:
            raise KeyError(f"agent {name!r} not registered")
        return self._agents[name]

    def list_names(self) -> list[str]:
        return list(self._agents.keys())

    def all(self) -> list[AgentMetadata]:
        return list(self._agents.values())

    # ----- capability advertise -------------------------------------

    def add_capability(self, name: str, capability: str) -> None:
        self._agents[name].capabilities.add(capability)

    def remove_capability(self, name: str, capability: str) -> None:
        self._agents[name].capabilities.discard(capability)

    def has_capability(self, name: str, capability: str) -> bool:
        if name not in self._agents:
            raise KeyError(f"agent {name!r} not registered")
        return capability in self._agents[name].capabilities

    # ----- discovery --------------------------------------------------

    def find_by_capability(self, capability: str) -> list[AgentMetadata]:
        matches: list[AgentMetadata] = []
        for meta in self._agents.values():
            if capability in meta.capabilities and meta.healthy:
                matches.append(meta)
        matches.sort(key=lambda m: (m.priority, m.name))
        return matches

    def best_match(self, capability: str) -> AgentMetadata | None:
        matches = self.find_by_capability(capability)
        return matches[0] if matches else None

    def advertise_all(self) -> dict[str, set[str]]:
        return {n: set(m.capabilities) for n, m in self._agents.items()}

    # ----- health ----------------------------------------------------

    def set_healthy(self, name: str, healthy: bool) -> None:
        if name not in self._agents:
            raise KeyError(f"agent {name!r} not registered")
        self._agents[name].healthy = healthy


__all__ = ["AgentMetadata", "AgentRegistry"]
