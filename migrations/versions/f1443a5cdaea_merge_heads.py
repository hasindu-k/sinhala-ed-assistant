"""Merge heads

Revision ID: f1443a5cdaea
Revises: 2f7c3f0a4e61, add_part_name_to_questions
Create Date: 2026-03-04 01:55:10.716466
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f1443a5cdaea'
down_revision: Union[str, None] = ('2f7c3f0a4e61', 'add_part_name_to_questions')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
