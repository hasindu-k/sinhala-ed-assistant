"""add part_name to questions

Revision ID: add_part_name_to_questions
Revises: 1db9252ab1f6
Create Date: 2026-02-28 17:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_part_name_to_questions'
down_revision: Union[str, None] = '1db9252ab1f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'questions',
        sa.Column('part_name', sa.String(), nullable=True),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_column('questions', 'part_name', if_exists=True)
