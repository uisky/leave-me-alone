"""task_tags

Revision ID: 452e31f23522
Revises: eae4261462f3
Create Date: 2020-06-02 01:14:21.717892

"""

# revision identifiers, used by Alembic.
revision = '452e31f23522'
down_revision = 'eae4261462f3'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('task_tags',
    sa.Column('task_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('task_id', 'name')
    )
    op.create_index(op.f('ix_task_tags_task_id'), 'task_tags', ['task_id'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_task_tags_task_id'), table_name='task_tags')
    op.drop_table('task_tags')
    # ### end Alembic commands ###