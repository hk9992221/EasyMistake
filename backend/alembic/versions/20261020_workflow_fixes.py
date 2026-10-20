"""Persist private grading records and index learning/background queries."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261020_workflow_fixes"
down_revision = "20260316_add_learning_progress"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("grading_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_name", sa.String(50), nullable=False),
        sa.Column("paper_name", sa.String(80), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("comment", sa.String(200), nullable=False),
        sa.CheckConstraint("score >= 0 AND score <= 150", name="ck_grading_score"),
    )
    op.create_index("ix_grading_records_user_id", "grading_records", ["user_id"])
    op.create_index("ix_questions_user_deleted_created", "questions", ["user_id", "is_deleted", "created_at", "id"])
    op.create_index("ix_attempts_user_question_submitted", "attempts", ["user_id", "question_id", "submitted_at"])
    op.create_index("ix_jobs_status_run_after", "jobs", ["status", "run_after"])
    op.create_index("ix_jobs_status_locked_at", "jobs", ["status", "locked_at"])


def downgrade():
    op.drop_index("ix_jobs_status_locked_at", table_name="jobs")
    op.drop_index("ix_jobs_status_run_after", table_name="jobs")
    op.drop_index("ix_attempts_user_question_submitted", table_name="attempts")
    op.drop_index("ix_questions_user_deleted_created", table_name="questions")
    op.drop_index("ix_grading_records_user_id", table_name="grading_records")
    op.drop_table("grading_records")
