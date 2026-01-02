"""update question_score model

Revision ID: 1f198b6304b6
Revises: 7d9bcc56b1f9
Create Date: 2026-01-01 13:51:34.366602
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1f198b6304b6'
down_revision: Union[str, None] = '7d9bcc56b1f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('question_scores', sa.Column('question_id', sa.UUID(), nullable=True))
    op.alter_column('question_scores', 'sub_question_id',
               existing_type=sa.UUID(),
               nullable=True)
    op.create_foreign_key(None, 'question_scores', 'questions', ['question_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint(None, 'question_scores', type_='foreignkey')
    op.alter_column('question_scores', 'sub_question_id',
               existing_type=sa.UUID(),
               nullable=False)
    op.drop_column('question_scores', 'question_id')
