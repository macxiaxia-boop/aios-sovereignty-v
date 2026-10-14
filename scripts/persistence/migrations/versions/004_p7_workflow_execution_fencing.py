"""P7 workflow execution fencing and external-effect journal.

Revision ID: 004
Revises: 003
Create Date: 2026-10-14

Only additive tables. Runtime create_all may have already initialized them;
this migration explicitly detects that case. It never discards task evidence.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())

    if "workflow_leases" not in tables:
        op.create_table(
            "workflow_leases",
            sa.Column("run_id", sa.String(length=64), primary_key=True),
            sa.Column("owner_id", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("fencing_token", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        )

    if "workflow_effects" not in tables:
        op.create_table(
            "workflow_effects",
            sa.Column("effect_key", sa.String(length=64), primary_key=True),
            sa.Column("run_id", sa.String(length=64), nullable=False),
            sa.Column("step_id", sa.String(length=128), nullable=False),
            sa.Column("request_hash", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False,
                      server_default="prepared"),
            sa.Column("receipt_json", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("reconciliation_evidence", sa.Text(), nullable=True),
        )

    # Existing create_all() installations already have the ORM-created index.
    indexes = {
        idx["name"] for idx in sa.inspect(bind).get_indexes("workflow_effects")
    }
    if "ix_workflow_effects_run_id" not in indexes:
        op.create_index(
            "ix_workflow_effects_run_id", "workflow_effects", ["run_id"],
        )


def downgrade() -> None:
    # These rows are audit/effect histories and a rollback would delete
    # evidence that may be needed to prevent duplicate remote side effects.
    raise RuntimeError(
        "P7 workflow ledger downgrade requires a separately approved, "
        "backed-up data migration; automatic table deletion is prohibited"
    )
