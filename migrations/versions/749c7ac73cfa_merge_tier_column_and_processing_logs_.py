"""merge tier column and processing_logs heads

Revision ID: 749c7ac73cfa
Revises: a71f6cdbcd77, c3a1f9d2e847
Create Date: 2026-03-11 02:27:51.068401
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '749c7ac73cfa'
down_revision: Union[str, None] = ('a71f6cdbcd77', 'c3a1f9d2e847')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
