"""Add computed severity, confidence score, and reliability fields

Revision ID: 1db9252ab1f6
Revises: a50819a1b526
Create Date: 2026-01-04 18:28:18.500178
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1db9252ab1f6'
down_revision: Union[str, None] = 'a50819a1b526'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('message_safety_reports', sa.Column('computed_severity', sa.String(), nullable=True))
    op.add_column('message_safety_reports', sa.Column('computed_confidence_score', sa.Numeric(), nullable=True))
    op.add_column('message_safety_reports', sa.Column('computed_reliability', sa.String(), nullable=True))
    

def downgrade() -> None:
    op.drop_column('message_safety_reports', 'computed_reliability')
    op.drop_column('message_safety_reports', 'computed_confidence_score')
    op.drop_column('message_safety_reports', 'computed_severity')