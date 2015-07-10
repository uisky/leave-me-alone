"""null statuses for tasks with children

Revision ID: 4ce61c1f756
Revises: 51a9dd090d7
Create Date: 2015-07-10 16:23:24.531774

"""

# revision identifiers, used by Alembic.
revision = '4ce61c1f756'
down_revision = '51a9dd090d7'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('tasks', 'status',
               existing_type=postgresql.ENUM('open', 'progress', 'pause', 'review', 'done', 'canceled', name='task_status'),
               nullable=True)
    op.execute("""
        UPDATE tasks set status = NULL
        WHERE
        (SELECT count(*) FROM tasks kids WHERE kids.parent_id = tasks.id) != 0
    """)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('tasks', 'status',
               existing_type=postgresql.ENUM('open', 'progress', 'pause', 'review', 'done', 'canceled', name='task_status'),
               nullable=False)
    ### end Alembic commands ###
