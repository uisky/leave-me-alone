"""new statuses


Revision ID: 32cc41a4f885
Revises: cc56e604e85b
Create Date: 2021-09-05 16:13:42.255048

"""

# revision identifiers, used by Alembic.
revision = '32cc41a4f885'
down_revision = 'cc56e604e85b'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute('ALTER TABLE tasks ALTER COLUMN status SET DATA TYPE varchar(32)')
    op.execute('DROP TYPE task_status CASCADE')
    op.execute("""
        CREATE TYPE task_status AS ENUM(
            'design.open', 'design.progress', 'design.pause',
            'dev.open', 'dev.progress', 'dev.pause', 'qa.open', 'qa.progress', 'qa.pause', 'qa.done',
            'review.open', 'review.progress', 'review.pause', 'review.done',
            'debug.open', 'debug.progress', 'debug.pause',
            'release.open', 'release.progress', 'release.pause',
            'complete',
            'canceled'
        )
    """)
    op.execute("""
        UPDATE tasks SET status = 'design.open' WHERE status = 'planning';
        UPDATE tasks SET status = 'dev.open' WHERE status = 'open';
        UPDATE tasks SET status = 'dev.progress' WHERE status = 'progress';
        UPDATE tasks SET status = 'dev.pause' WHERE status = 'pause';
        UPDATE tasks SET status = 'qa.open' WHERE status = 'review';
        UPDATE tasks SET status = 'qa.done' WHERE status = 'tested';
        UPDATE tasks SET status = 'complete' WHERE status = 'done';
    """)
    op.execute('ALTER TABLE tasks ALTER COLUMN status SET DATA TYPE task_status USING status::task_status')


def downgrade():
    op.execute('ALTER TABLE tasks ALTER COLUMN status SET DATA TYPE varchar(32)')
    op.execute('DROP TYPE task_status CASCADE')
    op.execute("CREATE TYPE task_status AS ENUM('planning', 'open', 'progress', 'pause', 'review', 'tested', 'done', 'canceled')")
    op.execute("""
        UPDATE tasks SET status = 'planning' WHERE status = 'design.open';
        UPDATE tasks SET status = 'open' WHERE status = 'dev.open';
        UPDATE tasks SET status = 'progress' WHERE status = 'dev.progress';
        UPDATE tasks SET status = 'pause' WHERE status = 'dev.pause';
        UPDATE tasks SET status = 'review' WHERE status = 'qa.open';
        UPDATE tasks SET status = 'tested' WHERE status = 'qa.done';
        UPDATE tasks SET status = 'done' WHERE status = 'complete';
    """)
    op.execute('ALTER TABLE tasks ALTER COLUMN status SET DATA TYPE task_status USING status::task_status')

