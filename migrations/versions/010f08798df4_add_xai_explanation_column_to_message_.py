"""Add xai_explanation column to message_safety_reports

Revision ID: 010f08798df4
Revises: f1443a5cdaea
Create Date: 2026-03-04 01:55:38.963456
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '010f08798df4'
down_revision: Union[str, None] = 'f1443a5cdaea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('message_safety_reports', sa.Column('xai_explanation', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('message_safety_reports', 'xai_explanation')
