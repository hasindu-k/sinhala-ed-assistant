"""add_user_evaluation_context

Revision ID: bab534582a40
Revises: change_rubric_weight_to_float
Create Date: 2025-12-29 12:53:25.444350
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'bab534582a40'
down_revision: Union[str, None] = 'change_rubric_weight_to_float'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
