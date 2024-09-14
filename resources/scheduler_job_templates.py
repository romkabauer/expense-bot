from datetime import datetime as dt, timedelta as td
from sqlalchemy import text
from aiogram import (
    Bot
)

from logger import Logger
from database.database import DatabaseFacade


async def job_send_message(user_id: int,
                           logger: Logger,
                           db: DatabaseFacade,
                           bot: Bot):
    with db.get_session() as db:
        db_payload = db.execute(text("SELECT 'Weekly report template'"))
        res = db_payload.first()[0]
    logger.log("Send Scheduled Message", str(user_id), str(res))
    week_start = (dt.now() - td(weeks=1)).strftime("%b %-d")
    week_end = dt.now().strftime("%b %-d")
    # await callback.message.answer(
    #     chat_id=user_id,
    #     text=f"*Weekly report for {week_start} \- {week_end}:*\n\n" + str(res),
    #     parse_mode="MarkdownV2"
    # )
