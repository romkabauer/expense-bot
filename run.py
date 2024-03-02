import asyncio
import datetime
import json
import logging

from bot import BotRunner


async def main():
    with open('config.json') as config_file:
        cfg = json.load(config_file)

    bot = BotRunner(config=cfg)
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
