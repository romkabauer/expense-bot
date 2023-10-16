from aiogram import types
from aiogram.utils.exceptions import MessageToDeleteNotFound
from aiogram.dispatcher import FSMContext

from handlers.base_handler import BaseHandler


class CancelHandler(BaseHandler):
    async def __call__(self, message: types.Message, state: FSMContext):
        async with state.proxy() as data:
            if data.get('init_instruction'):
                chat_id = message.from_user.id if message.chat == message.from_user.id else message.chat.id
                try:
                    await self.bot.delete_message(chat_id=chat_id,
                                                  message_id=data['init_instruction'])
                except MessageToDeleteNotFound:
                    pass
        await state.finish()
        await message.delete()


class HealthCheck(BaseHandler):
    async def __call__(self, message: types.Message):
        await message.reply("I'm alive, everything is perfect🙃", reply=True, disable_notification=True)