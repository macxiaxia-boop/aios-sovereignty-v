"""goal contract 12 fields (Phase F F001)

Adds 10 new columns to the ``goals`` table to support the full 12-field
GoalContract (see aios_kernel/domain/goal.py SCHEMA_VERSION=2):

    1.  stated_goal (title + description)        -- already present
    2.  inferred_intent                          -- NEW (nullable str)
    3.  preserve_capabilities                    -- NEW (JSON list[str])
    4.  known_constraints                        -- NEW (JSON list[Constraint])
    5.  environment_context                      -- NEW (JSON EnvSnapshot)
    6.  success_criteria                         -- already present
    7.  failure_modes                            -- NEW (JSON list[FailureMode])
    8.  permission_scope                         -- NEW (JSON PermissionScope)
    9.  missing_evidence                         -- NEW (JSON list[EvidenceRequest])
    10. approved_tradeoffs                       -- NEW (JSON list[Tradeoff])
    11. autonomous_scope                         -- NEW (JSON list[OpType])
    12. requires_authorization                   -- NEW (JSON list[OpType])

Each new column is nullable or defaults to empty so existing rows survive
the migration without backfill.

NOTE — Revision ID:
    The F001 card originally specified ``002_goal_contract_12_fields.py``.
    In Phase F, F003 had already landed a migration named
    ``002_decision_audit.py`` before F001 started, so this migration is
    numbered ``003`` and depends on ``002``. Downgrade removes only the
    F001 columns (forward-compatible rollback to the F003 schema).

Revision ID: 003
Revises: 002
Create Date: 2026-10-08
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 10 new GoalContract columns. SQLite JSON -> sa.JSON().
    op.add_column(
        "goals",
        sa.Column("inferred_intent", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "goals",
        sa.Column(
            "preserve_capabilities",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "goals",
        sa.Column(
            "known_constraints",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "goals",
        sa.Column("environment_context", sa.JSON(), nullable=True),
    )
    op.add_column(
        "goals",
        sa.Column(
            "failure_modes",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "goals",
        sa.Column("permission_scope", sa.JSON(), nullable=True),
    )
    op.add_column(
        "goals",
        sa.Column(
            "missing_evidence",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "goals",
        sa.Column(
            "approved_tradeoffs",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "goals",
        sa.Column(
            "autonomous_scope",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "goals",
        sa.Column(
            "requires_authorization",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    # Reverse-FK safe: SQLite supports drop_column since 3.35.
    op.drop_column("goals", "requires_authorization")
    op.drop_column("goals", "autonomous_scope")
    op.drop_column("goals", "approved_tradeoffs")
    op.drop_column("goals", "missing_evidence")
    op.drop_column("goals", "permission_scope")
    op.drop_column("goals", "failure_modes")
    op.drop_column("goals", "environment_context")
    op.drop_column("goals", "known_constraints")
    op.drop_column("goals", "preserve_capabilities")
    op.drop_column("goals", "inferred_intent")
