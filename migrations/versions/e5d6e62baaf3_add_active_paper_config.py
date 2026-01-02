"""add_active_paper_config

Revision ID: e5d6e62baaf3
Revises: bab534582a40
Create Date: 2025-12-29 13:22:04.159182
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e5d6e62baaf3'
down_revision: Union[str, None] = 'bab534582a40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user_evaluation_contexts', sa.Column('active_paper_config', sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('user_evaluation_contexts', 'active_paper_config')
