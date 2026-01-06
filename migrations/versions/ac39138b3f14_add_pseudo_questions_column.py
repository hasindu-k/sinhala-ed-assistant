"""Add pseudo_questions column

Revision ID: ac39138b3f14
Revises: 8dba69deca4f
Create Date: 2026-01-02 17:00:50.967467
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'ac39138b3f14'
down_revision: Union[str, None] = '8dba69deca4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('resource_chunks', sa.Column('pseudo_questions', sa.Text(), nullable=True))

def downgrade() -> None:
    op.drop_column('resource_chunks', 'pseudo_questions')
    