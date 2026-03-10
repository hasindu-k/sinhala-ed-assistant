"""set_parent_msg_fk_on_delete_cascade

Revision ID: 2f7c3f0a4e61
Revises: 1db9252ab1f6
Create Date: 2026-02-28 00:50:00.000000
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "2f7c3f0a4e61"
down_revision: Union[str, None] = "1db9252ab1f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE messages
        DROP CONSTRAINT IF EXISTS messages_parent_msg_id_fkey;

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'messages_parent_msg_id_fkey'
            ) THEN
                ALTER TABLE messages
                ADD CONSTRAINT messages_parent_msg_id_fkey
                FOREIGN KEY (parent_msg_id) REFERENCES messages(id) ON DELETE CASCADE;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE messages
        DROP CONSTRAINT IF EXISTS messages_parent_msg_id_fkey;

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
