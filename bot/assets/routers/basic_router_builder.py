import asyncio

from aiogram import (
    types,
    Router,
    Bot
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from static.interface_messages import HEALTH_CHECK
from static.literals import UILabels
from routers.abstract_router_builder import AbstractRouterBuilder
from logger import Logger


class BasicRouterBuilder(AbstractRouterBuilder):
    def __init__(self, logger: Logger):
        super().__init__(logger)
        self.router = Router(name=self.__class__.__name__)

    def build_default_router(self):
        self.router.message.register(self.handler_health_check,
                                     Command('alive'))
        self.router.message.register(self.handler_cancel,
                                     Command('cancel'))
        return self.router

    async def handler_health_check(self, message: types.Message):
        await message.delete()
        msg = await message.answer(
            text=HEALTH_CHECK,
            disable_notification=True
        )
        await asyncio.sleep(2)
        await msg.delete()

    async def handler_cancel(self, message: types.Message, state: FSMContext, bot: Bot):
        user_id = message.from_user.id
        data = await state.get_data()
        if data.get(UILabels.INIT_INSTRUCTION.value):
            chat_id = user_id if message.chat == user_id else message.chat.id
            try:
                await bot.delete_message(
                    chat_id=chat_id,
                    message_id=data[UILabels.INIT_INSTRUCTION.value]
                )
            except Exception as e:
                self.logger.log(self, level="error", user=user_id, extra_text=str(e))
        await state.clear()
        await message.delete()
