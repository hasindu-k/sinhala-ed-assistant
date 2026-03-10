"""add missing columns to questions

Revision ID: 4ac66e552875
Revises: 749c7ac73cfa
Create Date: 2026-03-11 02:28:38.885909
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '4ac66e552875'
down_revision: Union[str, None] = '749c7ac73cfa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('questions', sa.Column('question_type', sa.String(), nullable=True))
    op.add_column('questions', sa.Column('correct_answer', sa.String(), nullable=True))
    op.add_column('sub_questions', sa.Column('question_type', sa.String(), nullable=True))
    op.add_column('sub_questions', sa.Column('correct_answer', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('sub_questions', 'correct_answer')
    op.drop_column('sub_questions', 'question_type')
    op.drop_column('questions', 'correct_answer')
    op.drop_column('questions', 'question_type')