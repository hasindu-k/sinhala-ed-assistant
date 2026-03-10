"""Add tier column to users table

Revision ID: a71f6cdbcd77
Revises: 010f08798df4
Create Date: 2026-03-10 14:29:13.107138
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a71f6cdbcd77'
down_revision: Union[str, None] = '010f08798df4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('tier', sa.String(), nullable=True), if_not_exists=True)
    op.execute("UPDATE users SET tier = 'normal' WHERE tier IS NULL")
    op.alter_column('users', 'tier', nullable=False)

def downgrade() -> None:
    op.drop_column('users', 'tier', if_exists=True)
