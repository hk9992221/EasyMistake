"""fix_answer_images_column

Revision ID: 20260307_fix_answer_images
Revises: 20260307_add_answer_images
Create Date: 2026-03-07 01:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "20260307_fix_answer_images"
down_revision = "20260307_add_answer_images"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 删除 answers 表中的旧 answer_images 列
    op.drop_column("answers", "answer_images", schema=None)


def downgrade() -> None:
    # 回滚时恢复列（如果需要）
    op.add_column("answers", sa.Column("answer_images", sa.JSONB(), nullable=False))
