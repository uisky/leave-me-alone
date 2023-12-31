"""task_images

Revision ID: cc56e604e85b
Revises: 452e31f23522
Create Date: 2021-08-13 11:29:12.702951

"""

# revision identifiers, used by Alembic.
revision = 'cc56e604e85b'
down_revision = '452e31f23522'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('task_comments', sa.Column('_assets', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('tasks', sa.Column('_assets', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('tasks', '_assets')
    op.drop_column('task_comments', '_assets')
    # ### end Alembic commands ###
