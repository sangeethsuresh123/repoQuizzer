"""recreate repo_chunks without embedding_id column

Revision ID: d4e5f6a7b8c9
Revises: b10856e921cd
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa


revision = "d4e5f6a7b8c9"
down_revision = "b10856e921cd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("repo_chunks")
    op.create_table(
        "repo_chunks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("repo_id", sa.String(64), sa.ForeignKey("repos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("repo_chunks")
    op.create_table(
        "repo_chunks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("repo_id", sa.String(64), sa.ForeignKey("repos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding_id", sa.Text(), nullable=False),
    )
