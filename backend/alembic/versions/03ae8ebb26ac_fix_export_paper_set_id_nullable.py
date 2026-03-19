"""fix_export_paper_set_id_nullable

Revision ID: 03ae8ebb26ac
Revises: 0001_initial
Create Date: 2026-03-06 16:58:38.783446

"""
from alembic import op
import sqlalchemy as sa


revision = '03ae8ebb26ac'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Drop the foreign key constraint
    op.execute('ALTER TABLE exports DROP CONSTRAINT IF EXISTS exports_paper_set_id_fkey')

    # Step 2: Make the column nullable
    op.alter_column('exports', 'paper_set_id', nullable=True)

    # Step 3: Recreate the foreign key constraint with ON DELETE SET NULL
    op.execute('''
        ALTER TABLE exports
        ADD CONSTRAINT exports_paper_set_id_fkey
        FOREIGN KEY (paper_set_id)
        REFERENCES paper_sets(id)
        ON DELETE SET NULL
    ''')


def downgrade() -> None:
    # Reverse the changes
    # Step 1: Drop the foreign key constraint
    op.execute('ALTER TABLE exports DROP CONSTRAINT IF EXISTS exports_paper_set_id_fkey')

    # Step 2: Make the column not nullable (only works if no NULL values exist)
    op.execute('DELETE FROM exports WHERE paper_set_id IS NULL')
    op.alter_column('exports', 'paper_set_id', nullable=False)

    # Step 3: Recreate the foreign key constraint with ON DELETE CASCADE
    op.execute('''
        ALTER TABLE exports
        ADD CONSTRAINT exports_paper_set_id_fkey
        FOREIGN KEY (paper_set_id)
        REFERENCES paper_sets(id)
        ON DELETE CASCADE
    ''')
