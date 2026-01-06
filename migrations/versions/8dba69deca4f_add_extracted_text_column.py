"""Add extracted_text column

Revision ID: 8dba69deca4f
Revises: 1f198b6304b6
Create Date: 2026-01-02 15:24:03.710344
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8dba69deca4f'
down_revision: Union[str, None] = '1f198b6304b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This migration may be applied against databases where the column was added
    # manually or via earlier experiments. Make it idempotent.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "ALTER TABLE resource_files ADD COLUMN IF NOT EXISTS extracted_text TEXT"
        )
    else:
        # Fallback for other dialects (best-effort).
        inspector = sa.inspect(bind)
        existing = {col["name"] for col in inspector.get_columns("resource_files")}
        if "extracted_text" not in existing:
            op.add_column(
                "resource_files",
                sa.Column("extracted_text", sa.Text(), nullable=True),
            )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "ALTER TABLE resource_files DROP COLUMN IF EXISTS extracted_text"
        )
    else:
        inspector = sa.inspect(bind)
        existing = {col["name"] for col in inspector.get_columns("resource_files")}
        if "extracted_text" in existing:
            op.drop_column("resource_files", "extracted_text")
