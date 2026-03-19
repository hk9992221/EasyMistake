"""add_question_images_table

Revision ID: 20260307_add_question_images
Revises: 20260307_fix_answer_images
Create Date: 2026-03-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260307_add_question_images"
down_revision = "20260307_fix_answer_images"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 创建 question_images 表
    op.create_table(
        "question_images",
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("image_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["image_id"], ["images.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("question_id", "image_id")
    )

    # 2. 创建索引
    op.create_index("uq_question_images_order", "question_images", ["question_id", "order_index"], unique=True)
    op.create_index("ix_question_images_question_id", "question_images", ["question_id"])


def downgrade() -> None:
    # 删除 question_images 表
    op.drop_index("ix_question_images_question_id", table_name="question_images")
    op.drop_index("uq_question_images_order", table_name="question_images")
    op.drop_table("question_images")
