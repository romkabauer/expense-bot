"""Added message_id field for expenses

Revision ID: 4b09bc0493ba
Revises: 67c203042f1f
Create Date: 2024-05-04 21:00:36.493105

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b09bc0493ba'
down_revision: Union[str, None] = '67c203042f1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        table_name='expenses',
        column=sa.Column('message_id', sa.BigInteger(), nullable=True, server_default='0'),
        schema='expense_bot'
    )


def downgrade() -> None:
    op.drop_column(
        table_name='expenses',
        column_name='message_id',
        schema='expense_bot'
    )
