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
    op.execute("""
        MERGE INTO expense_bot.users_properties AS t
            USING (
                select
                  up.property_id,
                  up.user_id,
                  CASE
                    WHEN jsonb(property_value) ? 'Eat outside'
                      THEN jsonb(jsonb(property_value) - 'Eat outside' || jsonb_build_object('Eat Out', property_value->'Eat outside'))
                    ELSE jsonb(property_value)
                  END AS new_prop_value
                from expense_bot.users_properties up
                join expense_bot.properties p on up.property_id = p.id
                where p.name IN ('amounts', 'comments')
                
                union all
                
                select
                  property_id,
                  user_id,
                  CASE
                    WHEN jsonb_array_length(to_jsonb(property_value) - 'Eat outside') <> jsonb_array_length(to_jsonb(property_value))
                      THEN jsonb_insert(to_jsonb(property_value) - 'Eat outside', '{0}', '"Eat Out"')
                    ELSE to_jsonb(property_value)
                  END AS new_prop_value
                from expense_bot.users_properties up
                join expense_bot.properties p on up.property_id = p.id
                where p.name = 'categories'
            ) AS s
        ON t.property_id = s.property_id AND t.user_id = s.user_id
        WHEN MATCHED THEN
          UPDATE SET
            property_value = s.new_prop_value,
            updated_at = CURRENT_TIMESTAMP
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE expense_bot.categories SET name = 'Eat outside'
        WHERE name = 'Eat Out'
    """)
    op.execute("""
            MERGE INTO expense_bot.users_properties AS t
                USING (
                    select
                      up.property_id,
                      up.user_id,
                      CASE
                        WHEN jsonb(property_value) ? 'Eat Out'
                          THEN jsonb(jsonb(property_value) - 'Eat Out' || jsonb_build_object('Eat outside', property_value->'Eat Out'))
                        ELSE jsonb(property_value)
                      END AS new_prop_value
                    from expense_bot.users_properties up
                    join expense_bot.properties p on up.property_id = p.id
                    where p.name IN ('amounts', 'comments')

                    union all

                    select
                      property_id,
                      user_id,
                      CASE
                        WHEN jsonb_array_length(to_jsonb(property_value) - 'Eat Out') <> jsonb_array_length(to_jsonb(property_value))
                          THEN jsonb_insert(to_jsonb(property_value) - 'Eat Out', '{0}', '"Eat outside"')
                        ELSE to_jsonb(property_value)
                      END AS new_prop_value
                    from expense_bot.users_properties up
                    join expense_bot.properties p on up.property_id = p.id
                    where p.name = 'categories'
                ) AS s
            ON t.property_id = s.property_id AND t.user_id = s.user_id
            WHEN MATCHED THEN
              UPDATE SET
                property_value = s.new_prop_value,
                updated_at = CURRENT_TIMESTAMP
        """)
