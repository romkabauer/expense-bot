DEFAULT_WEEKLY_REPORT = """
WITH base_currency AS (
    SELECT
        user_id,
        COALESCE(property_value->>'base_currency', 'USD') AS base_currency
    FROM expense_bot.users_properties up
    LEFT JOIN expense_bot.properties p ON up.property_id = p.id
    WHERE
        p.name = 'base_currency'
        AND up.user_id = {{user_id}}
)

, base_expenses AS (
    SELECT
        e.id AS expense_id,
        c.name AS category_name,
        e.spent_on,
        COALESCE(
            CASE
                WHEN e.currency = bc.base_currency THEN e.amount
                ELSE e.amount /
                    nullif(((e.rates->>'rates')::json->>e.currency)::float, 0) * -- convert to base_currency (BC) from column rates
                    nullif(((e.rates->>'rates')::json->>bc.base_currency)::float, 0) -- convert to latest BC (mostly multiplies on 1, but crucial if BC on expense date differs from latest)
            END,
            e.amount)::decimal(15,2) AS amount_in_base_currency,
        bc.base_currency AS base_currency
    FROM expense_bot.expenses e
    LEFT JOIN expense_bot.categories c ON e.category_id = c.id
    LEFT JOIN base_currency bc ON e.user_id = bc.user_id
    WHERE
        e.user_id = {{user_id}}
        AND e.spent_on BETWEEN DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '28 days' AND CURRENT_DATE
        AND c.name NOT IN ('Rent')
    ORDER BY e.spent_on DESC, e.created_at DESC
)

, expenses_by_week AS (
    SELECT
        TO_CHAR(spent_on, 'YYYYWW') AS week,
        COALESCE(category_name, 'TOTAL') AS category_name,
        SUM(amount_in_base_currency) AS sum_amount,
        MAX(base_currency) AS base_currency
    FROM base_expenses e
    GROUP BY GROUPING SETS
        (TO_CHAR(spent_on, 'YYYYWW'), category_name),
        (TO_CHAR(spent_on, 'YYYYWW'))
)

, weeks_and_categories AS (
    SELECT
        DISTINCT w.week, c.name
    FROM expenses_by_week w
    CROSS JOIN expense_bot.categories c
    
    UNION ALL

    SELECT
        DISTINCT w.week, 'TOTAL'
    FROM expenses_by_week w
)

, prev_amounts AS (
    SELECT
        wc.week,
        wc.name,
        bc.base_currency,
        COALESCE(e.sum_amount, 0) AS sum_amount,
        COALESCE(LAG(e.sum_amount, 1) OVER(PARTITION BY wc.name ORDER BY wc.week), 0) AS prev_week_sum_amount,
        COALESCE(LAG(e.sum_amount, 4) OVER(PARTITION BY wc.name ORDER BY wc.week), 0) AS prev_month_week_sum_amount
    FROM weeks_and_categories wc
    LEFT JOIN expenses_by_week e ON wc.week = e.week AND wc.name = e.category_name
    CROSS JOIN base_currency bc
    ORDER BY 2, 1
)

SELECT
    week::varchar AS week,
    name AS category_name,
    sum_amount || ' ' || base_currency AS sum_amount,
    prev_week_sum_amount || ' ' || base_currency AS prev_week_sum_amount,
    prev_month_week_sum_amount || ' ' || base_currency AS prev_month_week_sum_amount,
    sum_amount - prev_week_sum_amount || ' ' || base_currency AS diff_prev_week,
    CASE
        WHEN sum_amount = 0 AND prev_week_sum_amount = 0 THEN '+0.00%'
        WHEN prev_week_sum_amount = 0 THEN '+100.00%'
        ELSE CASE WHEN sum_amount - prev_week_sum_amount > 0 THEN '+' ELSE '' END || ROUND((sum_amount - prev_week_sum_amount) / prev_week_sum_amount * 100, 2) || '%'
    END AS diff_prev_week_pct,
    sum_amount - prev_month_week_sum_amount || ' ' || base_currency AS diff_prev_month_week,
    CASE
        WHEN sum_amount = 0 AND prev_month_week_sum_amount = 0 THEN '+0.00%'
        WHEN prev_month_week_sum_amount = 0 THEN '+100.00%'
        ELSE CASE WHEN sum_amount - prev_month_week_sum_amount > 0 THEN '+' ELSE '' END || ROUND((sum_amount - prev_month_week_sum_amount) / prev_month_week_sum_amount * 100, 2) || '%'
    END AS diff_prev_month_week_pct
FROM prev_amounts pa
WHERE
    week = TO_CHAR(CURRENT_DATE, 'YYYYWW')
    AND NOT (prev_week_sum_amount = 0 AND sum_amount = 0)
ORDER BY pa.sum_amount DESC
"""