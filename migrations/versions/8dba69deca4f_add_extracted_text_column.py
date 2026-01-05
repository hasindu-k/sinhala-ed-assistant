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
    op.add_column(
        "resource_files",
        sa.Column("extracted_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("resource_files", "extracted_text")
