"""add paper_config fields

Revision ID: b63bd24fbee5
Revises: 19a8c12fb236
Create Date: 2025-12-23 10:52:53.309218
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b63bd24fbee5'
down_revision: Union[str, None] = '19a8c12fb236'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE paper_config
        ADD COLUMN paper_part VARCHAR,
        ADD COLUMN subject_name VARCHAR,
        ADD COLUMN medium VARCHAR,
        ADD COLUMN weightage NUMERIC(5,2),
        ADD COLUMN selection_rules JSONB,
        ADD COLUMN is_confirmed BOOLEAN DEFAULT FALSE
               
        ALTER TABLE questions
        ADD COLUMN shared_stem TEXT,
        ADD COLUMN inherits_shared_stem_from VARCHAR;
    """)



def downgrade() -> None:
    pass
