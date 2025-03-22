"""Change mp_unique_mission_id to mp_unique_id

Revision ID: 6597d02c847d
Revises: ebac182c168c
Create Date: 2025-03-22 16:19:01.414981

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6597d02c847d'
down_revision = 'ebac182c168c'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('mission_paparazzi_completed', 'mpc_unique_mission_id', new_column_name='mp_unique_id')

def downgrade():
    op.alter_column('mission_paparazzi_completed', 'mp_unique_id', new_column_name='mpc_unique_mission_id')

    op.create_table('_alembic_tmp_mission_paparazzi_completed',
    sa.Column('mpc_id', sa.INTEGER(), nullable=False),
    sa.Column('au_id', sa.INTEGER(), nullable=False),
    sa.Column('created_at', sa.DATETIME(), nullable=True),
    sa.Column('mpc_photo_path', sa.VARCHAR(length=255), nullable=True),
    sa.Column('mpc_coins', sa.INTEGER(), nullable=False),
    sa.Column('mpc_text', sa.TEXT(), nullable=True),
    sa.Column('mpc_status', sa.INTEGER(), nullable=True),
    sa.Column('mp_unique_id', sa.VARCHAR(length=50), nullable=False),
    sa.ForeignKeyConstraint(['au_id'], ['app_user.au_id'], ),
    sa.PrimaryKeyConstraint('mpc_id')
    )
    # ### end Alembic commands ###
