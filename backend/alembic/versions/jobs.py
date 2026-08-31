"""jobs: reclaim abandoned ingestion jobs, index the queue poll

Revision ID: 7c1e5a9b2f40
Revises: 3d2961d45c28
Create Date: 2026-10-04 04:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "7c1e5a9b2f40"
down_revision: str | Sequence[str] | None = "3d2961d45c28"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("ingestion_jobs") as batch:
        batch.add_column(sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_index("ix_ingestion_jobs_state_created_at", ["state", "created_at"])


def downgrade() -> None:
    with op.batch_alter_table("ingestion_jobs") as batch:
        batch.drop_index("ix_ingestion_jobs_state_created_at")
        batch.drop_column("claimed_at")
