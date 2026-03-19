"""add question_progress and enrich attempts for learning workflow

Revision ID: 20260316_add_learning_progress
Revises: 20260313_add_knowledge_points
Create Date: 2026-03-16 21:50:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260316_add_learning_progress"
down_revision = "20260313_add_knowledge_points"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("attempts", sa.Column("duration_sec", sa.Integer(), nullable=True))
    op.add_column("attempts", sa.Column("source", sa.String(length=64), nullable=True))
    op.add_column("attempts", sa.Column("review_mode", sa.String(length=64), nullable=True))
    op.add_column(
        "attempts",
        sa.Column(
            "error_tags_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column("attempts", sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE attempts SET submitted_at = occurred_at WHERE submitted_at IS NULL")
    op.alter_column("attempts", "submitted_at", nullable=False)

    op.create_table(
        "question_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wrong_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consecutive_correct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mastery_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("proficiency_score", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("self_assessment", sa.String(length=32), nullable=True),
        sa.Column("last_result", sa.String(length=16), nullable=True),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_stage", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_mastered", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "question_id", name="uq_question_progress_user_question"),
    )
    op.create_index("ix_question_progress_user_id", "question_progress", ["user_id"])
    op.create_index("ix_question_progress_question_id", "question_progress", ["question_id"])
    op.create_index("ix_question_progress_next_review_at", "question_progress", ["next_review_at"])
    op.create_index("ix_question_progress_is_mastered", "question_progress", ["is_mastered"])


def downgrade() -> None:
    op.drop_index("ix_question_progress_is_mastered", table_name="question_progress")
    op.drop_index("ix_question_progress_next_review_at", table_name="question_progress")
    op.drop_index("ix_question_progress_question_id", table_name="question_progress")
    op.drop_index("ix_question_progress_user_id", table_name="question_progress")
    op.drop_table("question_progress")

    op.drop_column("attempts", "submitted_at")
    op.drop_column("attempts", "error_tags_json")
    op.drop_column("attempts", "review_mode")
    op.drop_column("attempts", "source")
    op.drop_column("attempts", "duration_sec")
