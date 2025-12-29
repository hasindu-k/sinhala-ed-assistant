"""add rubric_id to chat_sessions

Revision ID: 6f895d2a9a3f
Revises: e5d6e62baaf3
Create Date: 2025-12-29 17:46:33.068601
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '6f895d2a9a3f'
down_revision: Union[str, None] = 'e5d6e62baaf3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('chat_sessions', sa.Column('rubric_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_chat_sessions_rubric_id', 'chat_sessions', 'rubrics', ['rubric_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_chat_sessions_rubric_id', 'chat_sessions', type_='foreignkey')
    op.drop_column('chat_sessions', 'rubric_id')
