"""change rubric weight to float

Revision ID: change_rubric_weight_to_float
Revises: b63bd24fbee5
Create Date: 2025-12-26 12:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'change_rubric_weight_to_float'
down_revision: Union[str, None] = 'b63bd24fbee5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Change weight_percentage from Integer to Float
    op.alter_column('rubric_criteria', 'weight_percentage',
                    existing_type=sa.Integer(),
                    type_=sa.Float(),
                    existing_nullable=True)


def downgrade() -> None:
    # Change weight_percentage back from Float to Integer
    op.alter_column('rubric_criteria', 'weight_percentage',
                    existing_type=sa.Float(),
                    type_=sa.Integer(),
                    existing_nullable=True)