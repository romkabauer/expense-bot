"""rename Eat outside to Eat Out

Revision ID: cf76b988cebb
Revises: 6cfa1e699a81
Create Date: 2024-08-18 00:18:46.299509

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf76b988cebb'
down_revision: Union[str, None] = '6cfa1e699a81'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE expense_bot.categories SET name = 'Eat Out'
        WHERE name = 'Eat outside'
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE expense_bot.categories SET name = 'Eat outside'
        WHERE name = 'Eat Out'
    """)
