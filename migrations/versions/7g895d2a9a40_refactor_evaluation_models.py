"""refactor_evaluation_models_to_chat_session

Revision ID: 7g895d2a9a40
Revises: 6f895d2a9a3f
Create Date: 2025-12-29 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7g895d2a9a40'
down_revision: Union[str, None] = '6f895d2a9a3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update question_papers table
    op.add_column(
        'question_papers',
        sa.Column('chat_session_id', sa.UUID(), nullable=True),
        if_not_exists=True,
    )
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_question_papers_chat_session_id'
            ) THEN
                ALTER TABLE question_papers
                ADD CONSTRAINT fk_question_papers_chat_session_id
                FOREIGN KEY (chat_session_id) REFERENCES chat_sessions(id);
            END IF;
        END $$;
    """)
    # We make evaluation_session_id nullable first, then we can drop it later or keep it for history if needed. 
    # For this refactor, we want to move ownership to chat_session.
    op.alter_column('question_papers', 'evaluation_session_id', nullable=True)
    
    # 2. Update paper_config table
    op.add_column(
        'paper_config',
        sa.Column('chat_session_id', sa.UUID(), nullable=True),
        if_not_exists=True,
    )
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_paper_config_chat_session_id'
            ) THEN
                ALTER TABLE paper_config
                ADD CONSTRAINT fk_paper_config_chat_session_id
                FOREIGN KEY (chat_session_id) REFERENCES chat_sessions(id);
            END IF;
        END $$;
    """)
    op.alter_column('paper_config', 'evaluation_session_id', nullable=True)


def downgrade() -> None:
    # Revert changes
    op.execute("""
        ALTER TABLE paper_config
        DROP CONSTRAINT IF EXISTS fk_paper_config_chat_session_id;
    """)
    op.drop_column('paper_config', 'chat_session_id', if_exists=True)
    op.alter_column('paper_config', 'evaluation_session_id', nullable=False)
    
    op.execute("""
        ALTER TABLE question_papers
        DROP CONSTRAINT IF EXISTS fk_question_papers_chat_session_id;
    """)
    op.drop_column('question_papers', 'chat_session_id', if_exists=True)
    op.alter_column('question_papers', 'evaluation_session_id', nullable=False)
