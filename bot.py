from aiogram import Bot, Dispatcher
from aiogram.types.bot_command import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage

from handlers import (
    BasicHandlersRouterBuilder,
    SetupHandlersRouterBuilder,
    ExpenseHandlersRouterBuilder,
)
from resources.states import States
from logger import Logger


class BotRunner:
    def __init__(self, bot_token: str):
        self.bot = Bot(token=bot_token)
        self.dispatcher = Dispatcher(storage=MemoryStorage())
        self.logger = Logger()
        self.states = States

    def register_handlers(self):
        basic_router = BasicHandlersRouterBuilder()
        basic_router = basic_router.build_default_router()

        setup_router = SetupHandlersRouterBuilder()
        setup_router = setup_router.build_default_router()

        expense_router = ExpenseHandlersRouterBuilder()
        expense_router = expense_router.build_default_router()

        self.dispatcher.include_routers(*[basic_router, expense_router, setup_router])

    async def on_startup(self, *args):
        await self.bot.set_my_commands(
            [
                BotCommand(command='add', description='add expense'),
                BotCommand(command='shortcut', description='add via shortcuts for frequent expenses'),
                BotCommand(command='cancel', description='terminate the flow of the current command'),
                BotCommand(command='setup', description='setup properties to start using bot'),
                BotCommand(command='settings', description='change bot settings'),
                BotCommand(command='alive', description='check if bot is available'),
            ]
        )

    async def shutdown(self, *args):
        await self.dispatcher.storage.close()
