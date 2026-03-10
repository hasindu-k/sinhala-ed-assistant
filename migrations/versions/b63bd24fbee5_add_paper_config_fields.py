"""add paper_config fields

Revision ID: b63bd24fbee5
Revises: 19a8c12fb236
Create Date: 2025-12-23 10:52:53.309218
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b63bd24fbee5'
down_revision: Union[str, None] = '19a8c12fb236'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'paper_config',
        sa.Column('paper_part', sa.String(), nullable=True),
        if_not_exists=True,
    )
    op.add_column(
        'paper_config',
        sa.Column('subject_name', sa.String(), nullable=True),
        if_not_exists=True,
    )
    op.add_column(
        'paper_config',
        sa.Column('medium', sa.String(), nullable=True),
        if_not_exists=True,
    )
    op.add_column(
        'paper_config',
        sa.Column('weightage', sa.Numeric(5, 2), nullable=True),
        if_not_exists=True,
    )
    op.add_column(
        'paper_config',
        sa.Column('selection_rules', sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        if_not_exists=True,
    )
    op.add_column(
        'paper_config',
        sa.Column('is_confirmed', sa.Boolean(), nullable=True, server_default=sa.text('FALSE')),
        if_not_exists=True,
    )

    op.add_column(
        'questions',
        sa.Column('shared_stem', sa.Text(), nullable=True),
        if_not_exists=True,
    )
    op.add_column(
        'questions',
        sa.Column('inherits_shared_stem_from', sa.String(), nullable=True),
        if_not_exists=True,
    )



def downgrade() -> None:
    op.drop_column('questions', 'inherits_shared_stem_from', if_exists=True)
    op.drop_column('questions', 'shared_stem', if_exists=True)

    op.drop_column('paper_config', 'is_confirmed', if_exists=True)
    op.drop_column('paper_config', 'selection_rules', if_exists=True)
    op.drop_column('paper_config', 'weightage', if_exists=True)
    op.drop_column('paper_config', 'medium', if_exists=True)
    op.drop_column('paper_config', 'subject_name', if_exists=True)
    op.drop_column('paper_config', 'paper_part', if_exists=True)
