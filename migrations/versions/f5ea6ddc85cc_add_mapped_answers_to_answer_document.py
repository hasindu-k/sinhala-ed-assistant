"""add_mapped_answers_to_answer_document

Revision ID: f5ea6ddc85cc
Revises: 7g895d2a9a40
Create Date: 2025-12-30 18:27:38.815357
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f5ea6ddc85cc'
down_revision: Union[str, None] = '7g895d2a9a40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('answer_documents', sa.Column('mapped_answers', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('answer_documents', 'mapped_answers')
