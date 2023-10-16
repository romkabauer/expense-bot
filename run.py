from aiogram import executor
import datetime
import json

from bot import BotRunner


def load_config():
    with open('config.json') as config_file:
        cfg = json.load(config_file)
    return cfg


if __name__ == '__main__':
    config = load_config()
    bot = BotRunner(config=config)
    bot.register_handlers()
    bot.logger.info(f"Started: {datetime.datetime.now()}")
    executor.start_polling(dispatcher=bot.dispatcher,
                           on_startup=bot.on_startup,
                           on_shutdown=bot.shutdown,
                           skip_updates=True)
