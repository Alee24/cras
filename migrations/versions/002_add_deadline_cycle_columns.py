"""Add cycle and previous due date columns to compliance_deadlines

Revision ID: 002_deadline_cycles
Revises: 
Create Date: 2026-11-17 09:30:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '002_deadline_cycles'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_cols = [c['name'] for c in inspector.get_columns('compliance_deadlines')]
    
    with op.batch_alter_table('compliance_deadlines', schema=None) as batch_op:
        if 'last_completed_due_date' not in existing_cols:
            batch_op.add_column(sa.Column('last_completed_due_date', sa.Date(), nullable=True))
        if 'completed_cycle_until' not in existing_cols:
            batch_op.add_column(sa.Column('completed_cycle_until', sa.Date(), nullable=True))


def downgrade():
    with op.batch_alter_table('compliance_deadlines', schema=None) as batch_op:
        batch_op.drop_column('completed_cycle_until')
        batch_op.drop_column('last_completed_due_date')
