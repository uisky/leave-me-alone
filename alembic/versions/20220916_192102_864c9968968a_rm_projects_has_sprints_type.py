"""rm projects.has_sprints, type

Revision ID: 864c9968968a
Revises: 89a60f0e0fe1
Create Date: 2022-09-16 19:21:02.118642

"""

# revision identifiers, used by Alembic.
revision = '864c9968968a'
down_revision = '89a60f0e0fe1'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('projects', 'type')
    op.drop_column('projects', 'has_sprints')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('projects', sa.Column('has_sprints', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False))
    op.add_column('projects', sa.Column('type', postgresql.ENUM('tree', 'list', 'stickers', 'bubbles', name='project_type'), server_default=sa.text("'tree'::project_type"), autoincrement=False, nullable=False))
    # ### end Alembic commands ###