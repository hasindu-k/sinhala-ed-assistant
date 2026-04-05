"""Add processing_logs table

Revision ID: c3a1f9d2e847
Revises: 010f08798df4
Create Date: 2026-03-10 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision: str = 'c3a1f9d2e847'
down_revision: Union[str, None] = '010f08798df4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("SET search_path TO public")

    op.execute("""
        CREATE TABLE IF NOT EXISTS processing_logs (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            resource_id UUID NOT NULL REFERENCES resource_files(id) ON DELETE CASCADE,
            user_id     UUID REFERENCES users(id) ON DELETE SET NULL,
            session_id  UUID REFERENCES chat_sessions(id) ON DELETE SET NULL,
            message_id  UUID REFERENCES messages(id) ON DELETE SET NULL,
            stage       VARCHAR NOT NULL,
            progress    FLOAT NOT NULL,
            details     JSONB,
            timestamp   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_processing_logs_resource_id ON processing_logs(resource_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_processing_logs_user_id     ON processing_logs(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_processing_logs_session_id  ON processing_logs(session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_processing_logs_message_id  ON processing_logs(message_id)")


def downgrade() -> None:
    op.drop_index('idx_processing_logs_message_id',  table_name='processing_logs')
    op.drop_index('idx_processing_logs_session_id',  table_name='processing_logs')
    op.drop_index('idx_processing_logs_user_id',     table_name='processing_logs')
    op.drop_index('idx_processing_logs_resource_id', table_name='processing_logs')
    op.drop_table('processing_logs')
