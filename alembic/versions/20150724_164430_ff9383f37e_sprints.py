"""sprints

Revision ID: ff9383f37e
Revises: 5998315b99a
Create Date: 2015-07-24 16:44:30.637141

"""

# revision identifiers, used by Alembic.
revision = 'ff9383f37e'
down_revision = '5998315b99a'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('sprints',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('start', sa.Date(), server_default=sa.text('current_date'), nullable=False),
        sa.Column('finish', sa.Date(), server_default=sa.text('current_date + 7'), nullable=False),

        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], onupdate='CASCADE', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sprints_project_id'), 'sprints', ['project_id'], unique=False)
    op.add_column('projects', sa.Column('has_sprints', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('tasks', sa.Column('sprint_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_tasks_sprint_id'), 'tasks', ['sprint_id'], unique=False)
    op.create_foreign_key(None, 'tasks', 'sprints', ['sprint_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'tasks', type_='foreignkey')
    op.drop_index(op.f('ix_tasks_sprint_id'), table_name='tasks')
    op.drop_column('tasks', 'sprint_id')
    op.drop_column('projects', 'has_sprints')
    op.drop_index(op.f('ix_sprints_project_id'), table_name='sprints')
    op.drop_table('sprints')
    ### end Alembic commands ###