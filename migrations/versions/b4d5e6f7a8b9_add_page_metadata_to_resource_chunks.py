"""add page metadata to resource chunks

Revision ID: b4d5e6f7a8b9
Revises: a8b3c4d5e6f7
Create Date: 2026-03-31 18:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4d5e6f7a8b9"
down_revision: Union[str, None] = "a8b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "resource_chunks",
        sa.Column("page_number", sa.Integer(), nullable=True),
        if_not_exists=True,
    )
    op.add_column(
        "resource_chunks",
        sa.Column("lesson_title", sa.String(), nullable=True),
        if_not_exists=True,
    )
    op.add_column(
        "resource_chunks",
        sa.Column("section_title", sa.String(), nullable=True),
        if_not_exists=True,
    )
    op.create_index(op.f("ix_resource_chunks_page_number"), "resource_chunks", ["page_number"], unique=False)

    op.execute(
        """
        UPDATE resource_chunks
        SET page_number = CAST((regexp_match(content, '---\\s*PAGE\\s+(\\d+)\\s*---', 'i'))[1] AS INTEGER)
        WHERE page_number IS NULL
          AND content ~* '---\\s*PAGE\\s+\\d+\\s*---'
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_resource_chunks_page_number"), table_name="resource_chunks")
    op.drop_column("resource_chunks", "section_title", if_exists=True)
    op.drop_column("resource_chunks", "lesson_title", if_exists=True)
    op.drop_column("resource_chunks", "page_number", if_exists=True)
