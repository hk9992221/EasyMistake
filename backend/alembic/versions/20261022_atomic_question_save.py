"""Deduplicate complete question saves by user and client request."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261022_atomic_question_save"
down_revision = "20261020_workflow_fixes"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("questions", sa.Column("client_request_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("questions", sa.Column("client_payload_hash", sa.String(64), nullable=True))
    op.create_unique_constraint("uq_questions_user_client_request", "questions", ["user_id", "client_request_id"])


def downgrade():
    op.drop_constraint("uq_questions_user_client_request", "questions", type_="unique")
    op.drop_column("questions", "client_payload_hash")
    op.drop_column("questions", "client_request_id")
