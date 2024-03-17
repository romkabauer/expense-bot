import asyncio
import datetime
import logging
import os

from bot import BotRunner


async def main():
    bot_token = os.getenv("EXPENSE_BOT_TOKEN")
    if not bot_token:
        raise KeyError("EXPENSE_BOT_TOKEN environment variable should be specified!")

    bot = BotRunner(bot_token=bot_token)
    await bot.on_startup()
    bot.register_handlers()
    bot.logger.log(bot, "admin", extra_text=f"Bot started: {datetime.datetime.now()}")
    await bot.dispatcher.start_polling(bot.bot)
    await bot.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")
