"""add source metadata to marking schema items

Revision ID: a8b3c4d5e6f7
Revises: f2c1d9a6b7e0
Create Date: 2026-03-31 17:45:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8b3c4d5e6f7"
down_revision: Union[str, None] = "f2c1d9a6b7e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "marking_schema_items",
        sa.Column("source_lessons", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        if_not_exists=True,
    )
    op.add_column(
        "marking_schema_items",
        sa.Column("source_pages", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        if_not_exists=True,
    )
    op.add_column(
        "marking_schema_items",
        sa.Column("source_notes", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_column("marking_schema_items", "source_notes", if_exists=True)
    op.drop_column("marking_schema_items", "source_pages", if_exists=True)
    op.drop_column("marking_schema_items", "source_lessons", if_exists=True)
