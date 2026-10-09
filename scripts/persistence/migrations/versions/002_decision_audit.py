"""decision audit log (Phase F F003)

Adds the ``decision_audit`` table for the Cognitive Governance plane.
Every AIOS decision (route dispatch, intent parse, failure merge, etc.)
writes one row, forming a verifiable chain per goal / per actor.

Schema mirrors DecisionAudit in aios_kernel.domain.decision. FK to goals
uses ON DELETE CASCADE so purging a goal removes its audit chain with it.

Indexes (per F003 acceptance criteria):
  - ix_decision_audit_goal_id  : per-goal chain lookup
  - ix_decision_audit_actor    : per-actor history
  - ix_decision_audit_outcome  : pending-list sweep

Revision ID: 002
Revises: 001
Create Date: 2026-10-08
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "decision_audit",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "goal_id",
            sa.String(length=36),
            sa.ForeignKey("goals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actor", sa.String(length=64), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("alternatives", sa.JSON(), nullable=False),
        sa.Column("chosen", sa.String(length=64), nullable=False),
        sa.Column(
            "outcome",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("outcome_detail", sa.Text(), nullable=True),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
            server_default="1.0",
        ),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("envelope_json", sa.JSON(), nullable=False),
        sa.Column(
            "schema_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_decision_audit_goal_id", "decision_audit", ["goal_id"])
    op.create_index("ix_decision_audit_actor", "decision_audit", ["actor"])
    op.create_index("ix_decision_audit_outcome", "decision_audit", ["outcome"])


def downgrade() -> None:
    # Drop indexes first (reverse order), then the table.
    op.drop_index("ix_decision_audit_outcome", table_name="decision_audit")
    op.drop_index("ix_decision_audit_actor", table_name="decision_audit")
    op.drop_index("ix_decision_audit_goal_id", table_name="decision_audit")
    op.drop_table("decision_audit")