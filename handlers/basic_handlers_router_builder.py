import time

from aiogram import (
    types,
    Router
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from handlers.abstract_router_builder import AbstractRouterBuilder
from resources import interface_messages


class BasicHandlersRouterBuilder(AbstractRouterBuilder):
    def __init__(self):
        super().__init__()
        self.router = Router(name=self.__class__.__name__)

    def build_default_router(self):
        self.router.message.register(self.handler_health_check,
                                     Command('alive'))
        self.router.message.register(self.handler_cancel,
                                     Command('cancel'))
        return self.router

    async def handler_health_check(self, message: types.Message, state: FSMContext):
        await message.delete()
        await state.set_state(self.state.shortcut)
        msg = await message.answer(text=interface_messages.HEALTH_CHECK,
                                   disable_notification=True)
        time.sleep(2)
        await msg.delete()

    async def handler_cancel(self, message: types.Message, state: FSMContext, bot):
        data = await state.get_data()
        if data.get('init_instruction'):
            chat_id = message.from_user.id if message.chat == message.from_user.id else message.chat.id
            try:
                await bot.delete_message(chat_id=chat_id,
                                         message_id=data['init_instruction'])
            except Exception as e:
                self.logger.log(self, message.from_user.id, str(e), level="error")
        await state.clear()
        await message.delete()
