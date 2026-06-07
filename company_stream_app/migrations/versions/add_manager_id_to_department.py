"""add manager_id column to department (replace lead)

Revision ID: add_manager_id
Revises: f2c775a17312
Create Date: 2026-06-07 17:28:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_manager_id'
down_revision = 'f2c775a17312'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('department', schema=None) as batch_op:
        batch_op.add_column(sa.Column('manager_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True))
        batch_op.drop_column('lead')


def downgrade():
    with op.batch_alter_table('department', schema=None) as batch_op:
        batch_op.add_column(sa.Column('lead', sa.VARCHAR(length=120), nullable=True))
        batch_op.drop_column('manager_id')