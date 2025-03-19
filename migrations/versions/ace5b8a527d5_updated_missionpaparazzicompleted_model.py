"""Updated MissionPaparazziCompleted model

Revision ID: ace5b8a527d5
Revises: 3199284142c4
Create Date: 2025-03-19 14:54:11.775111

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ace5b8a527d5'
down_revision = '3199284142c4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('equivalent', schema=None) as batch_op:
        batch_op.alter_column('eq_created_at',
               existing_type=sa.DATETIME(),
               nullable=True)

    with op.batch_alter_table('mission_paparazzi_completed', schema=None) as batch_op:
        batch_op.add_column(sa.Column('mpc_mission_id', sa.String(length=50), nullable=False))
        batch_op.add_column(sa.Column('mpc_photo_path', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('mpc_coins', sa.Integer(), nullable=False))
        batch_op.add_column(sa.Column('mpc_text', sa.Text(), nullable=True))
        batch_op.drop_column('total_coins')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('mission_paparazzi_completed', schema=None) as batch_op:
        batch_op.add_column(sa.Column('total_coins', sa.INTEGER(), nullable=False))
        batch_op.drop_column('mpc_text')
        batch_op.drop_column('mpc_coins')
        batch_op.drop_column('mpc_photo_path')
        batch_op.drop_column('mpc_mission_id')

    with op.batch_alter_table('equivalent', schema=None) as batch_op:
        batch_op.alter_column('eq_created_at',
               existing_type=sa.DATETIME(),
               nullable=False)

    # ### end Alembic commands ###
