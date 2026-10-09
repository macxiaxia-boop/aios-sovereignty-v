"""initial schema

Phase A T0030 §8: 8 tables (6 main + 2 auxiliary).
- 6 main: goals, tasks, plans, artifacts, evidences, traces
- 2 auxiliary: worker_runs, verifier_runs

All time columns are timezone-aware (DateTime(timezone=True)) so the DB
rejects naive datetimes — matches Pydantic envelope.utcnow().

Indexes per T0032 acceptance criteria:
- tasks(goal_id, status)  → ix_tasks_goal_status
- plans(goal_id, version) → ix_plans_goal_version
- traces(task_id, span_id lookup) → ix_traces_task + JSON span id index

Revision ID: 001
Revises:
Create Date: 2026-10-08
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- goals (root aggregate) ----
    op.create_table(
        "goals",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("success_criteria", sa.Text(), nullable=False),
        sa.Column("budget", sa.Float(), nullable=False, server_default="0"),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Pending"),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("plan_ids", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("envelope_json", sa.JSON(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_goals_status", "goals", ["status"])
    op.create_index("ix_goals_owner", "goals", ["owner"])

    # ---- plans (must exist before tasks, since tasks.plan_id FKs here) ----
    op.create_table(
        "plans",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("goal_id", sa.String(length=36), sa.ForeignKey("goals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("parent_version", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rollback_to", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.String(length=100), nullable=False, server_default="system"),
        sa.Column("steps", sa.JSON(), nullable=False),
        sa.Column("dependencies", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("envelope_json", sa.JSON(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_plans_goal_version", "plans", ["goal_id", "version"])
    op.create_index("ix_plans_goal_active", "plans", ["goal_id", "is_active"])

    # ---- tasks (FK goals + plans) ----
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("goal_id", sa.String(length=36), sa.ForeignKey("goals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("task_type", sa.String(length=30), nullable=False, server_default="custom"),
        sa.Column("worker", sa.String(length=100), nullable=True),
        sa.Column("plan_id", sa.String(length=36), sa.ForeignKey("plans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("plan_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Pending"),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("artifact_ids", sa.JSON(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("cost_yuan", sa.Float(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("output_payload", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("envelope_json", sa.JSON(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tasks_goal_status", "tasks", ["goal_id", "status"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_worker", "tasks", ["worker"])

    # ---- artifacts (FK tasks) ----
    op.create_table(
        "artifacts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_id", sa.String(length=36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("artifact_type", sa.String(length=20), nullable=False, server_default="file"),
        sa.Column("path", sa.String(length=2000), nullable=True),
        sa.Column("inline_content", sa.Text(), nullable=True),
        sa.Column("inline_json", sa.JSON(), nullable=True),
        sa.Column("hash_sha256", sa.String(length=64), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("label", sa.String(length=200), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("envelope_json", sa.JSON(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_artifacts_task", "artifacts", ["task_id"])
    op.create_index("ix_artifacts_hash", "artifacts", ["hash_sha256"])

    # ---- evidences (FK tasks; verdict column is the canonical one) ----
    op.create_table(
        "evidences",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_id", sa.String(length=36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("artifact_ids", sa.JSON(), nullable=False),
        sa.Column("verifier_id", sa.String(length=100), nullable=False),
        sa.Column("verdict", sa.String(length=10), nullable=False, server_default="BLOCKED"),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recheck_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("cost_yuan", sa.Float(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("evidence_hash", sa.String(length=64), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("envelope_json", sa.JSON(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evidences_task", "evidences", ["task_id"])
    op.create_index("ix_evidences_verifier_verdict", "evidences", ["verifier_id", "verdict"])

    # ---- traces (FK goals + tasks; spans JSON for TraceSpan list) ----
    op.create_table(
        "traces",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("goal_id", sa.String(length=36), sa.ForeignKey("goals.id", ondelete="CASCADE"), nullable=True),
        sa.Column("task_id", sa.String(length=36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True),
        sa.Column("workflow_run_id", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False, server_default="trace"),
        sa.Column("spans", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("envelope_json", sa.JSON(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_traces_goal", "traces", ["goal_id"])
    op.create_index("ix_traces_task", "traces", ["task_id"])
    op.create_index("ix_traces_workflow", "traces", ["workflow_run_id"])

    # ---- worker_runs (audit) ----
    op.create_table(
        "worker_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_id", sa.String(length=36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("worker_name", sa.String(length=100), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="running"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("artifact_ids", sa.JSON(), nullable=False),
        sa.Column("cost_yuan", sa.Float(), nullable=False, server_default="0"),
        sa.Column("payload", sa.JSON(), nullable=False),
    )
    op.create_index("ix_worker_runs_task", "worker_runs", ["task_id"])
    op.create_index("ix_worker_runs_status", "worker_runs", ["status"])

    # ---- verifier_runs (audit) ----
    op.create_table(
        "verifier_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_id", sa.String(length=36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("verifier_id", sa.String(length=100), nullable=False),
        sa.Column("evidence_id", sa.String(length=36), sa.ForeignKey("evidences.id", ondelete="SET NULL"), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verdict", sa.String(length=10), nullable=False, server_default="BLOCKED"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("cost_yuan", sa.Float(), nullable=False, server_default="0"),
        sa.Column("payload", sa.JSON(), nullable=False),
    )
    op.create_index("ix_verifier_runs_task", "verifier_runs", ["task_id"])
    op.create_index("ix_verifier_runs_verdict", "verifier_runs", ["verdict"])


def downgrade() -> None:
    # Drop in reverse-FK order.
    op.drop_table("verifier_runs")
    op.drop_table("worker_runs")
    op.drop_table("traces")
    op.drop_table("evidences")
    op.drop_table("artifacts")
    op.drop_table("tasks")
    op.drop_table("plans")
    op.drop_table("goals")
