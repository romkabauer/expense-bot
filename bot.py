import os
from aiogram import (
    Bot,
    Dispatcher
)
from aiogram.types.bot_command import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler_di import ContextSchedulerDecorator

from handlers import (
    BasicHandlersRouterBuilder,
    SetupHandlersRouterBuilder,
    ExpenseHandlersRouterBuilder,
    ScheduleHandlersRouterBuilder
)
from resources.states import States
from logger import Logger


class BotRunner:
    def __init__(self, bot_token: str):
        self.bot = Bot(token=bot_token)
        self.dispatcher = Dispatcher(storage=MemoryStorage())
        self.logger = Logger()
        self.states = States
        self.scheduler = ContextSchedulerDecorator(
            AsyncIOScheduler(jobstores={
                "default": SQLAlchemyJobStore(
                    url=os.environ["JOB_STORE_DB_CONNECTION_STRING"]
                )
            })
        )
        self.scheduler.ctx.add_instance(self.bot, Bot)
        self.scheduler.start()

    def register_handlers(self):
        basic_router = BasicHandlersRouterBuilder()
        basic_router = basic_router.build_default_router()

        setup_router = SetupHandlersRouterBuilder()
        setup_router = setup_router.build_default_router()

        expense_router = ExpenseHandlersRouterBuilder()
        expense_router = expense_router.build_default_router()

        schedule_router = ScheduleHandlersRouterBuilder(self.scheduler)
        schedule_router = schedule_router.build_default_router()

        self.dispatcher.include_routers(*[basic_router, expense_router, setup_router, schedule_router])

    async def on_startup(self, *args):
        await self.bot.set_my_commands(
            [
                BotCommand(command='add', description='add expense'),
                BotCommand(command='shortcut', description='add via shortcuts for frequent expenses'),
                BotCommand(command='cancel', description='terminate the flow of the current command'),
                BotCommand(command='analytics', description='get link and credentials to analytics'),
                BotCommand(command='reset_analytics', description='reset link and credentials to analytics'),
                BotCommand(command='settings', description='change bot settings'),
                BotCommand(command='start', description='setup properties to start using bot'),
                BotCommand(command='reset', description='reset properties to default'),
                BotCommand(command='alive', description='check if bot is available'),
            ]
        )

    async def shutdown(self, *args):
        await self.dispatcher.storage.close()
