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
    op.add_column('user_evaluation_contexts', sa.Column('active_rubric_resource_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_user_eval_ctx_rubric_res_id', 'user_evaluation_contexts', 'resource_files', ['active_rubric_resource_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_user_eval_ctx_rubric_res_id', 'user_evaluation_contexts', type_='foreignkey')
    op.drop_column('user_evaluation_contexts', 'active_rubric_resource_id')
