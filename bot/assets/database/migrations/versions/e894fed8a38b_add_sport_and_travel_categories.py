"""add sport and travel categories

Revision ID: 6cfa1e699a81
Revises: 4b09bc0493ba
Create Date: 2024-08-18 00:09:11.237960

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6cfa1e699a81'
down_revision: Union[str, None] = '4b09bc0493ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        MERGE INTO expense_bot.categories AS t
            USING (
                SELECT
                  COALESCE(
                    (SELECT id FROM expense_bot.categories WHERE name = 'Travel'),
                    gen_random_uuid()
                  ) AS id, 'Travel' AS name
                  
                UNION ALL
                
                SELECT
                  COALESCE(
                    (SELECT id FROM expense_bot.categories WHERE name = 'Sport & Wellness'),
                    gen_random_uuid()
                  ) AS id, 'Sport & Wellness' AS name
              ) AS s
    ON t.id = s.id
    WHEN MATCHED THEN
      UPDATE SET
        name = s.name
    WHEN NOT MATCHED THEN
      INSERT (id, name) VALUES (s.id, s.name)
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE expense_bot.expenses SET
            category_id = (SELECT id FROM expense_bot.categories WHERE name = 'Other')
        WHERE category_id IN (
            SELECT id FROM expense_bot.categories WHERE name IN (
                'Travel',
                'Sport & Wellness'
            )
        )
    """)
    op.execute("""
        DELETE FROM expense_bot.categories
            WHERE name IN (
                'Travel',
                'Sport & Wellness'
            )
    """)
