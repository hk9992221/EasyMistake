"""add_answer_images_table

Revision ID: 20260307_add_answer_images
Revises: 03ae8ebb26ac
Create Date: 2026-03-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260307_add_answer_images"
down_revision = "03ae8ebb26ac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 创建 answer_images 表
    op.create_table(
        "answer_images",
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("image_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["image_id"], ["images.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("question_id", "image_id")
    )

    # 2. 创建索引
    op.create_index("uq_answer_images_order", "answer_images", ["question_id", "order_index"], unique=True)
    op.create_index("ix_answer_images_question_id", "answer_images", ["question_id"])

    # 3. 迁移现有的单图片数据到 answer_images 表（如果有）
    op.execute("""
        INSERT INTO answer_images (question_id, image_id, order_index, created_at)
        SELECT
            a.question_id,
            i.id as image_id,
            1 as order_index,
            a.created_at
        FROM answers a
        JOIN images i ON a.answer_image_key = i.object_key
        WHERE a.answer_image_key IS NOT NULL
        ON CONFLICT (question_id, image_id) DO NOTHING
    """)

    # 4. 移除 answers 表的单图片字段
    op.drop_column("answers", "answer_image_url")
    op.drop_column("answers", "answer_image_key")


def downgrade() -> None:
    # 1. 恢复单图片字段（如果需要回滚）
    op.add_column("answers", sa.Column("answer_image_key", sa.String(length=512), nullable=True))
    op.add_column("answers", sa.Column("answer_image_url", sa.String(length=1024), nullable=True))

    # 2. 从 answer_images 迁移数据回 answers 表（可选，只迁移第一张图片）
    op.execute("""
        UPDATE answers a
        SET
            answer_image_key = i.object_key,
            answer_image_url = i.storage_url
        FROM answer_images ai
        JOIN images i ON ai.image_id = i.id
        WHERE a.question_id = ai.question_id
          AND ai.order_index = 1
    """)

    # 3. 删除 answer_images 表
    op.drop_index("ix_answer_images_question_id", table_name="answer_images")
    op.drop_index("uq_answer_images_order", table_name="answer_images")
    op.drop_table("answer_images")
