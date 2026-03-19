"""add knowledge_points_json to questions

Revision ID: 20260313_add_knowledge_points
Revises: 005f5cfcaf65
Create Date: 2026-03-13 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260313_add_knowledge_points"
down_revision = "005f5cfcaf65"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "questions",
        sa.Column(
            "knowledge_points_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("questions", "knowledge_points_json")
