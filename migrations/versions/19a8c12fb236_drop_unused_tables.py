"""drop_unused_tables

Revision ID: 19a8c12fb236
Revises: 40876970d3e2
Create Date: 2025-12-21 01:02:07.610038
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '19a8c12fb236'
down_revision: Union[str, None] = '40876970d3e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop tables
    op.drop_table('user_question_paper')
    op.drop_table('chat_messages')
    op.drop_table('chunks')


def downgrade() -> None:
    # Recreate user_question_paper table
    op.create_table(
        'user_question_paper',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.String, nullable=True),
        sa.Column('raw_text', sa.Text, nullable=True),
        sa.Column('cleaned_text', sa.Text, nullable=True),
        sa.Column('structured_questions', sa.JSON, nullable=True),
        sa.Column('total_main_questions', sa.Integer, nullable=True),
        sa.Column('sub_questions_per_main', sa.Integer, nullable=True),
        sa.UniqueConstraint('user_id', name='ix_user_question_paper_user_id')
    )
    op.create_index('ix_user_question_paper_id', 'user_question_paper', ['id'])

    # Recreate chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.UUID, primary_key=True),
        sa.Column('session_id', sa.UUID, nullable=False),
        sa.Column('sender', sa.Enum('sender_enum', name='sender_enum'), nullable=False),
        sa.Column('message', sa.Text, nullable=True),
        sa.Column('tokens_used', sa.Integer, nullable=True),
        sa.Column('audio_url', sa.Text, nullable=True),
        sa.Column('image_url', sa.Text, nullable=True),
        sa.Column('file_id', sa.UUID, nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True)
    )

    # Recreate chunks table
    op.create_table(
        'chunks',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('ocr_document_id', sa.UUID, nullable=True),
        sa.Column('chunk_id', sa.Integer, nullable=True),
        sa.Column('global_id', sa.String, nullable=True),
        sa.Column('text', sa.Text, nullable=True),
        sa.Column('numbering', sa.String, nullable=True),
        sa.Column('embedding', sa.dialects.postgresql.ARRAY(sa.Float), nullable=True)  # adjust if vector type is different
    )
    op.create_foreign_key(
        'chunks_ocr_document_id_fkey',
        'chunks', 'ocr_documents',
        ['ocr_document_id'], ['id']
    )
