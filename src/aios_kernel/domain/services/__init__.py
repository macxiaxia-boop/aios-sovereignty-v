"""aios_kernel.domain.services — Orchestration layer (T0032).

Services are thin: they take a Pydantic domain object, write it to the
persistence layer, and emit events (logs / future message bus). They do
NOT do workflow scheduling (T0033), worker dispatch (T0034), or verification
(T0035). The pattern is:

    GoalService.create_goal(input) -> Goal   # allocate id, persist
    TaskService.transition(task, new) -> Task  # state machine, persist
    PlanService.create_version(plan) -> Plan   # auto-increment, persist
    DecisionService.record(...) -> DecisionAudit  # F003
"""
from aios_kernel.domain.services.decision_service import DecisionService
from aios_kernel.domain.services.goal_service import GoalService
from aios_kernel.domain.services.plan_service import PlanService
from aios_kernel.domain.services.task_service import TaskService

__all__ = ["GoalService", "TaskService", "PlanService", "DecisionService"]