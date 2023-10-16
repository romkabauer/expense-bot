from aiogram import Bot, Dispatcher
from aiogram.types.bot_command import BotCommand
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware


from handlers.basic_handlers import CancelHandler, HealthCheck
from handlers.expenses import StartAddingExpense, \
    InputDate, ParseDate, \
    ParseAmount, AskAmount, \
    InputComment, ParseComment
from resources.states import States
from logger import Logger


class BotRunner:
    def __init__(self, config: dict):
        self.bot = Bot(token=config.get("bot_token"))
        self.config = config
        self.dispatcher = Dispatcher(self.bot, storage=MemoryStorage())
        self.dispatcher.middleware.setup(LoggingMiddleware())
        self.logger = Logger()
        self.states = States

    def register_handlers(self):
        # IS_ADMIN_CONDITION = lambda c: c.from_user.id in self.admins
        base_properties = self.bot, self.states, self.logger, self.config

        self.dispatcher.register_message_handler(
            CancelHandler(*base_properties),
            commands=['cancel'],
            state='*')
        self.dispatcher.register_message_handler(
            HealthCheck(*base_properties),
            commands='alive')
        self.dispatcher.register_message_handler(
            StartAddingExpense(*base_properties),
            # IS_ADMIN_CONDITION,
            commands='add')

        self.dispatcher.register_callback_query_handler(
            InputDate(*base_properties),
            lambda c: c.data in ["today", "yesterday", "other_date"])
        self.dispatcher.register_message_handler(
            ParseDate(*base_properties),
            state=self.states.picking_day)

        self.dispatcher.register_callback_query_handler(
            AskAmount(*base_properties),
            lambda c: c.data in self.config.get("spending_categories"),
            state="*")

        self.dispatcher.register_message_handler(
            ParseAmount(*base_properties),
            state=self.states.entering_amount)

        self.dispatcher.register_callback_query_handler(
            InputComment(*base_properties),
            lambda c: c.data in self.config.get("comments"),
            state="*")
        self.dispatcher.register_message_handler(
            ParseComment(*base_properties),
            state=self.states.commenting)

    async def on_startup(self, *args):
        await self.bot.set_my_commands(
            [
                BotCommand('add', 'add expense'),
                BotCommand('cancel', 'terminate the flow of the current command'),
                BotCommand('alive', 'check if bot is available'),
            ]
        )

    async def shutdown(self, *args):
        await self.dispatcher.storage.close()
        await self.dispatcher.storage.wait_closed()
