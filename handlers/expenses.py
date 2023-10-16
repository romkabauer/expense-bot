from aiogram import types
from aiogram.dispatcher import FSMContext
import re
from datetime import datetime as dt, timedelta as td

from handlers.base_handler import BaseHandler
from resources.keyboards import build_date_keyboard, build_listlike_keyboard


class StartAddingExpense(BaseHandler):
    async def __call__(self, message: types.Message, state: FSMContext):
        msg = await message.reply("📅When did you spend?",
                                  reply_markup=build_date_keyboard(),
                                  reply=False,
                                  disable_notification=True)
        await self.save_init_instruction_msg_id(msg, state)
        await message.delete()


class InputDate(BaseHandler):
    async def __call__(self, callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()

        if callback.data in ["today", "yesterday"]:
            msg = await callback.message.reply("🛍️What is the expense category?",
                                               reply_markup=build_listlike_keyboard(
                                                   entities=self.config.get("spending_categories"),
                                                   max_items_in_a_row=3),
                                               reply=False,
                                               disable_notification=True)
            await self.save_init_instruction_msg_id(msg, state)

            when_value = dt.now().strftime('%Y-%m-%d') if callback.data == "today" \
                else (dt.now() - td(1)).strftime('%Y-%m-%d')
            await self.fill_payload_field(field_key="when", value=when_value, state=state)
        else:
            msg = await callback.message.reply("🔤Input expense date in format '2023-10-13':",
                                               reply=False,
                                               disable_notification=True)
            await self.save_init_instruction_msg_id(msg, state)
            await self.state.picking_day.set()

        await callback.message.delete()


class ParseDate(BaseHandler):
    async def __call__(self, message: types.Message, state: FSMContext):
        await message.delete()

        if not re.match(r"20\d{2}-(1[0-2]|0[1-9])-(3[0-1]|1[0-9]|2[0-9]|0[1-9])", message.text):
            await self.delete_init_instruction(message.chat.id, state)
            msg = await message.reply(text=f"⛔️Wrong date format.\n"
                                           f"🔤Input expense date in format '2023-10-13':",
                                      reply=False,
                                      disable_notification=True)
            await self.save_init_instruction_msg_id(msg, state)
            return

        elif dt.strptime(message.text, '%Y-%m-%d') > dt.now():
            await self.delete_init_instruction(message.chat.id, state)
            msg = await message.reply(text=f"⛔️Input cannot contain future dates.\n"
                                           f"🔤Input expense date in format '2023-10-13':",
                                      reply=False,
                                      disable_notification=True)
            await self.save_init_instruction_msg_id(msg, state)
            return

        await self.delete_init_instruction(message.chat.id, state)

        msg = await message.reply("🛍️What is the expense category?",
                                  reply_markup=build_listlike_keyboard(self.config.get('spending_categories')),
                                  reply=False,
                                  disable_notification=True)
        await self.save_init_instruction_msg_id(msg, state)
        await self.fill_payload_field(field_key="when", value=message.text, state=state)


class AskAmount(BaseHandler):
    async def __call__(self, callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        await callback.message.delete()

        await self.fill_payload_field(field_key="category", value=callback.data, state=state)

        msg = await callback.message.reply("💵What is an amount paid?",
                                           reply=False,
                                           disable_notification=True)
        await self.save_init_instruction_msg_id(msg, state)

        await self.state.entering_amount.set()


class ParseAmount(BaseHandler):
    async def __call__(self, message: types.Message, state: FSMContext):
        await message.delete()
        await self.delete_init_instruction(chat_id=message.chat.id, state=state)

        if not re.match(r"\d+([.,]\d+)?", message.text):
            msg = await message.reply(text=f"⛔️Wrong format for spending amount.\n"
                                           f"🔤Should contain only positive numbers "
                                           f"possibly with . or , decimal separator:",
                                      reply=False,
                                      disable_notification=True)
            await self.save_init_instruction_msg_id(msg, state)
            return

        msg = await message.reply(text=f"🔤Choose any comment to add or choose 'Custom comment' and write custom one:",
                                  reply_markup=build_listlike_keyboard(self.config.get("comments")),
                                  reply=False,
                                  disable_notification=True)
        await self.save_init_instruction_msg_id(msg, state)

        await self.fill_payload_field(field_key="amount", value=message.text, state=state)


class InputComment(BaseHandler):
    async def __call__(self, callback: types.CallbackQuery, state: FSMContext):
        if callback.data == "Custom comment":
            msg = await callback.message.reply("🔤Input your comment:",
                                               reply=False,
                                               disable_notification=True)
            await self.save_init_instruction_msg_id(msg, state)
            await callback.message.delete()
            await self.state.commenting.set()
        else:
            await self.fill_payload_field(field_key="comment", value=callback.data, state=state)
            await self.send_form_response(chat_id=callback.message.chat.id, state=state)
            await callback.message.delete()
            await state.finish()


class ParseComment(BaseHandler):
    async def __call__(self, message: types.Message, state: FSMContext):
        await self.delete_init_instruction(message.chat.id, state)
        await self.fill_payload_field(field_key="comment", value=message.text, state=state)
        await self.send_form_response(chat_id=message.chat.id, state=state)
        await message.delete()
        await state.finish()
