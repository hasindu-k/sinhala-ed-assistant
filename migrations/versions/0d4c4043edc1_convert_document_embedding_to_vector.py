"""Convert document_embedding to vector

Revision ID: 0d4c4043edc1
Revises: 1db9252ab1f6
Create Date: 2026-01-06 10:23:08.829464
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0d4c4043edc1'
down_revision: Union[str, None] = '1db9252ab1f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Ensure pgvector extension exists.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Only alter if the column is not already a pgvector column.
    row = bind.execute(
        sa.text(
            """
            SELECT data_type, udt_name
            FROM information_schema.columns
            WHERE table_name = 'resource_files'
              AND column_name = 'document_embedding'
            """
        )
    ).fetchone()

    if not row:
        return

    data_type, udt_name = row
    if udt_name == "vector":
        return

    # Convert existing JSON arrays (e.g. [0.1, 0.2, ...]) to vector.
    # json::text renders the array as bracketed text, which pgvector can parse.
    # We defensively strip spaces.
    op.execute(
        """
        ALTER TABLE resource_files
        ALTER COLUMN document_embedding
        TYPE vector(768)
        USING (
            CASE
                WHEN document_embedding IS NULL THEN NULL
                ELSE replace(document_embedding::text, ' ', '')::vector(768)
            END
        )
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    row = bind.execute(
        sa.text(
            """
            SELECT data_type, udt_name
            FROM information_schema.columns
            WHERE table_name = 'resource_files'
              AND column_name = 'document_embedding'
            """
        )
    ).fetchone()

    if not row:
        return

    _, udt_name = row
    if udt_name != "vector":
        return

    # Convert vector text representation (e.g. [0.1,0.2,...]) back to JSON.
    op.execute(
        """
        ALTER TABLE resource_files
        ALTER COLUMN document_embedding
        TYPE json
        USING (document_embedding::text::json)
        """
    )
