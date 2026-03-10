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
    op.add_column(
        'chat_sessions',
        sa.Column('rubric_id', sa.UUID(), nullable=True),
        if_not_exists=True,
    )
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_chat_sessions_rubric_id'
            ) THEN
                ALTER TABLE chat_sessions
                ADD CONSTRAINT fk_chat_sessions_rubric_id
                FOREIGN KEY (rubric_id) REFERENCES rubrics(id);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE chat_sessions
        DROP CONSTRAINT IF EXISTS fk_chat_sessions_rubric_id;
    """)
    op.drop_column('chat_sessions', 'rubric_id', if_exists=True)
