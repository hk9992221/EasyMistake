"""fix_answer_images_column

Revision ID: 20260307_fix_answer_images
Revises: 20260307_add_answer_images
Create Date: 2026-03-07 01:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260307_fix_answer_images"
down_revision = "20260307_add_answer_images"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Some older installations had this legacy column; the initial migration did not.
    op.execute("ALTER TABLE answers DROP COLUMN IF EXISTS answer_images")


def downgrade() -> None:
    # 回滚时恢复列（如果需要）
    op.add_column("answers", sa.Column("answer_images", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")))
