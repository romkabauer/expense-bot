"""add scheduled jobs parameter

Revision ID: 89c796ed0292
Revises: cf76b988cebb
Create Date: 2024-09-28 18:06:09.559417

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '89c796ed0292'
down_revision: Union[str, None] = 'cf76b988cebb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
            MERGE INTO expense_bot.properties AS t
                USING (
                    SELECT
                      COALESCE(
                        (SELECT id FROM expense_bot.properties WHERE name = 'scheduled_jobs'),
                        gen_random_uuid()
                      ) AS id, 'scheduled_jobs' AS name, FALSE AS is_required
                  ) AS s
        ON t.id = s.id
        WHEN MATCHED THEN
          UPDATE SET
            name = s.name,
            is_required = s.is_required
        WHEN NOT MATCHED THEN
          INSERT (id, name, is_required) VALUES (s.id, s.name, s.is_required)
        """)


def downgrade() -> None:
    op.execute("""
            DELETE FROM expense_bot.users_properties
            WHERE property_id = (
                SELECT id FROM expense_bot.properties
                WHERE name = 'scheduled_jobs'
            )
        """)
    op.execute("""
            DELETE FROM expense_bot.properties
                WHERE name IN (
                    'scheduled_jobs'
                )
        """)
