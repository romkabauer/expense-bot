from aiogram import Bot
from abc import abstractmethod

from resources.states import States
from logger import Logger


class BaseHandler:
    def __init__(self, bot: Bot, states: States, logger: Logger, config: dict):
        self.bot = bot
        self.state = states
        self.logger = logger
        self.config = config

    @abstractmethod
    async def __call__(self, *args, **kwargs):
        pass
