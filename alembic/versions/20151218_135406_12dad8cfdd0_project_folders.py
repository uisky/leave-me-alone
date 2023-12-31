"""project folders

Revision ID: 12dad8cfdd0
Revises: 3fd4f49118e
Create Date: 2015-12-18 13:54:06.464361

"""

# revision identifiers, used by Alembic.
revision = '12dad8cfdd0'
down_revision = '3fd4f49118e'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('project_folders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('in_menu', sa.Boolean(), server_default='t', nullable=False),
    sa.Column('bgcolor', sa.String(length=6), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_project_folders_user_id'), 'project_folders', ['user_id'], unique=False)

    op.add_column('project_members', sa.Column('folder_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'project_members', 'project_folders', ['folder_id'], ['id'], onupdate='CASCADE', ondelete='SET NULL')
    op.drop_column('project_members', 'archived')

    # Раздаём всем папку "Архив"
    op.execute("INSERT INTO project_folders (user_id, name, in_menu) SELECT id, 'Архив', false FROM users")

    op.alter_column('projects', 'type',
               existing_type=postgresql.ENUM('tree', 'list', 'stickers', 'bubbles', name='project_type'),
               type_=postgresql.ENUM('tree', 'list', name='project_type'),
               existing_nullable=False,
               existing_server_default=sa.text("'tree'::project_type"))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('projects', 'type',
               existing_type=postgresql.ENUM('tree', 'list', name='project_type'),
               type_=postgresql.ENUM('tree', 'list', 'stickers', 'bubbles', name='project_type'),
               existing_nullable=False,
               existing_server_default=sa.text("'tree'::project_type"))
    op.add_column('project_members', sa.Column('archived', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'project_members', type_='foreignkey')
    op.drop_column('project_members', 'folder_id')
    op.drop_index(op.f('ix_project_folders_user_id'), table_name='project_folders')
    op.drop_table('project_folders')
    ### end Alembic commands ###
