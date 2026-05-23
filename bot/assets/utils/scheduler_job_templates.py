from datetime import datetime as dt, timedelta as td
import os

from aiogram import Bot
from aiogram.types.input_file import FSInputFile, InputFile
from sqlalchemy.sql import text

from static.analytics_sql_templates import DEFAULT_WEEKLY_REPORT
from database.database import DatabaseFacade
from logger import Logger
from utils.bi_interface import SupersetInterface


async def job_send_message(user_id: int,
                           logger: Logger,
                           db: DatabaseFacade,
                           bot: Bot,
                           dashboard_name: str | None):
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

    logger.log(job_send_message, user=user_id, extra_text=res)
    week_start = (dt.now() - td(weeks=1)).strftime("%b %-d")
    week_end = dt.now().strftime("%b %-d")

    await bot.send_message(
        chat_id=user_id,
        text=f"*Weekly report for {week_start} \- {week_end}:*\n\n" + str(res),
        parse_mode="MarkdownV2"
    )

    if dashboard_name and db_payload:
        chart_path = None
        try:
            bi_interface = SupersetInterface(logger=logger)
            chart_path = await bi_interface.get_dashboard_image(
                dashboard_name,
                target_user_id=user_id,
            )
            await bot.send_photo(
                chat_id=user_id,
                photo=FSInputFile(chart_path)
            )
            logger.log(job_send_message.__name__, user=user_id, extra_text=f"Screenshot of '{dashboard_name}' dashboard sent.")
        except Exception as e:
            logger.log(job_send_message.__name__, user=user_id, extra_text=f"Failed to send chart: {e}")
        finally:
            if chart_path and os.path.exists(chart_path):
                os.remove(chart_path)
