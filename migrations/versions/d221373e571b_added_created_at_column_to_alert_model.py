"""Added created_at column to Alert model

Revision ID: d221373e571b
Revises: 
Create Date: 2025-02-26 13:35:39.263320

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d221373e571b"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("alert", schema=None) as batch_op:
        batch_op.add_column(sa.Column("a_created_at", sa.DateTime(), nullable=True))

    # Set default value for existing records
    op.execute("UPDATE alert SET a_created_at = CURRENT_TIMESTAMP")
    # ### end Alembic commands ###

    # Alter column to be non-nullable
    with op.batch_alter_table('alert', schema=None) as batch_op:
        batch_op.alter_column('a_created_at', nullable=False)


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("alert", schema=None) as batch_op:
        batch_op.drop_column("a_created_at")

    # ### end Alembic commands ###
