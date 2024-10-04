from datetime import datetime as dt, timedelta as td

from aiogram import (
    Bot
)
from sqlalchemy.sql import text

from logger import Logger
from database.database import DatabaseFacade
from resources.analytics_sql_templates import DEFAULT_WEEKLY_REPORT


async def job_send_message(user_id: int,
                           logger: Logger,
                           db: DatabaseFacade,
                           bot: Bot):
    sql_for_report = DEFAULT_WEEKLY_REPORT.replace("{{user_id}}", str(user_id))
    with db.get_session() as db:
        db_payload = db.execute(text(sql_for_report)).mappings().all()

    if not db_payload:
        res = "Not enough data for report\."
    else:
        res = ""
        for row in db_payload:
            trend_icon = "🔴 " if "+" in row['diff_prev_week_pct'] else "🟢 "
            not_esc_res = (f"*{trend_icon}{row['category_name']} - {row['sum_amount']}* "
                    f"\(vs {row['prev_week_sum_amount']} on prev week - "
                    f"{row['diff_prev_week_pct']} / {row['diff_prev_week']}\)"
                    "\n")
            res += not_esc_res.replace(".", "\.") \
                              .replace("+", "\+") \
                              .replace("-", "\-")

    logger.log("Send Scheduled Message", str(user_id), str(res))
    week_start = (dt.now() - td(weeks=1)).strftime("%b %-d")
    week_end = dt.now().strftime("%b %-d")
    await bot.send_message(
        chat_id=user_id,
        text=f"*Weekly report for {week_start} \- {week_end}:*\n\n" + str(res),
        parse_mode="MarkdownV2"
    )
