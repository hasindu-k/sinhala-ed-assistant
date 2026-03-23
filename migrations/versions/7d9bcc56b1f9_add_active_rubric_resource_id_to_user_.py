"""add_active_rubric_resource_id_to_user_context

Revision ID: 7d9bcc56b1f9
Revises: f5ea6ddc85cc
Create Date: 2025-12-30 19:13:09.957569
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7d9bcc56b1f9'
down_revision: Union[str, None] = 'f5ea6ddc85cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'user_evaluation_contexts',
        sa.Column('active_rubric_resource_id', sa.UUID(), nullable=True),
        if_not_exists=True,
    )
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_user_eval_ctx_rubric_res_id'
            ) THEN
                ALTER TABLE user_evaluation_contexts
                ADD CONSTRAINT fk_user_eval_ctx_rubric_res_id
                FOREIGN KEY (active_rubric_resource_id) REFERENCES resource_files(id);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE user_evaluation_contexts
        DROP CONSTRAINT IF EXISTS fk_user_eval_ctx_rubric_res_id;
    """)
    op.drop_column('user_evaluation_contexts', 'active_rubric_resource_id', if_exists=True)
