"""Make facebook_link unique.

Revision ID: 709722e7d87c
Revises: 10bd26c8b3bd
Create Date: 2020-11-06 18:57:15.382607

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '709722e7d87c'
down_revision = '10bd26c8b3bd'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint(None, 'artists', ['facebook_link'])
    op.create_unique_constraint(None, 'venues', ['facebook_link'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'venues', type_='unique')
    op.drop_constraint(None, 'artists', type_='unique')
    # ### end Alembic commands ###