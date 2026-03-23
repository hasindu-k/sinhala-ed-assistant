"""add_parent_msg_id_to_messages

Revision ID: a50819a1b526
Revises: ac39138b3f14
Create Date: 2026-01-03 09:21:12.425603
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a50819a1b526'
down_revision: Union[str, None] = 'ac39138b3f14'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'messages',
        sa.Column('parent_msg_id', sa.UUID(), nullable=True),
        if_not_exists=True,
    )
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'messages_parent_msg_id_fkey'
            ) THEN
                ALTER TABLE messages
                ADD CONSTRAINT messages_parent_msg_id_fkey
                FOREIGN KEY (parent_msg_id) REFERENCES messages(id);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE messages
        DROP CONSTRAINT IF EXISTS messages_parent_msg_id_fkey;
    """)
    op.drop_column('messages', 'parent_msg_id', if_exists=True)