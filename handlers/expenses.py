from aiogram import types
from aiogram.dispatcher import FSMContext
import json
import re
import requests as r
from datetime import datetime as dt, timedelta as td

from handlers.base_handler import BaseHandler
from resources.keyboards import build_date_keyboard, build_listlike_keyboard
from resources.form_sender import get_default_form_payload


class StartAddingExpense(BaseHandler):
    async def __call__(self, message: types.Message, state: FSMContext):
        msg = await message.reply("📅When did you spend?",
                                  reply_markup=build_date_keyboard(),
                                  reply=False,
                                  disable_notification=True)
        async with state.proxy() as data:
            data['init_instruction'] = msg["message_id"]
        await message.delete()


class InputDate(BaseHandler):
    async def __call__(self, callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()

        if callback.data in ["today", "yesterday"]:
            msg = await callback.message.reply("🛍️What is the expense category?",
                                               reply_markup=build_listlike_keyboard(
                                                   entities=self.config.get('spending_categories'),
                                                   max_items_in_a_row=3),
                                               reply=False,
                                               disable_notification=True)
            async with state.proxy() as data:
                data["init_instruction"] = msg["message_id"]
                if not data.get("form_payload"):
                    data["form_payload"] = get_default_form_payload(self.config.get("form_payload_template"))

                year_key = [key for key in data["form_payload"].keys() if "year" in key][0]
                month_key = [key for key in data["form_payload"].keys() if "month" in key][0]
                day_key = [key for key in data["form_payload"].keys() if "day" in key][0]

                data["form_payload"][year_key] = dt.now().year if callback.data == "today" \
                    else (dt.now() - td(1)).year
                data["form_payload"][month_key] = dt.now().month if callback.data == "today" \
                    else (dt.now() - td(1)).month
                data["form_payload"][day_key] = dt.now().day if callback.data == "today" \
                    else (dt.now() - td(1)).day
        else:
            msg = await callback.message.reply("🔤Input expense date in format '2023-10-13':",
                                               reply=False,
                                               disable_notification=True)
            async with state.proxy() as data:
                data['init_instruction'] = msg["message_id"]
            await self.state.picking_day.set()

        await callback.message.delete()


class ParseDate(BaseHandler):
    async def __call__(self, message: types.Message, state: FSMContext):
        await message.delete()
        async with state.proxy() as data:
            init_msg_to_delete = data.get('init_instruction')

        if not re.match(r"20\d{2}-(1[0-2]|0[1-9])-(3[0-1]|1[0-9]|2[0-9]|0[1-9])", message.text):
            await self.bot.delete_message(chat_id=message.chat.id,
                                          message_id=init_msg_to_delete)

            msg = await message.reply(text=f"⛔️Wrong date format.\n"
                                           f"🔤Input expense date in format '2023-10-13':",
                                      reply=False,
                                      disable_notification=True)
            async with state.proxy() as data:
                data['init_instruction'] = msg["message_id"]
            return
        elif dt.strptime(message.text, '%Y-%m-%d') > dt.now():
            await self.bot.delete_message(chat_id=message.chat.id,
                                          message_id=init_msg_to_delete)

            msg = await message.reply(text=f"⛔️Input cannot contain future dates.\n"
                                           f"🔤Input expense date in format '2023-10-13':",
                                      reply=False,
                                      disable_notification=True)
            async with state.proxy() as data:
                data['init_instruction'] = msg["message_id"]
            return

        await self.bot.delete_message(chat_id=message.chat.id,
                                      message_id=init_msg_to_delete)

        msg = await message.reply("🛍️What is the expense category?",
                                  reply_markup=build_listlike_keyboard(self.config.get('spending_categories')),
                                  reply=False,
                                  disable_notification=True)
        async with state.proxy() as data:
            data['init_instruction'] = msg["message_id"]
            if not data.get('form_payload'):
                data['form_payload'] = get_default_form_payload(self.config.get("form_payload_template"))
            date_parts = message.text.split('-')

            year_key = [key for key in data["form_payload"].keys() if "year" in key][0]
            month_key = [key for key in data["form_payload"].keys() if "month" in key][0]
            day_key = [key for key in data["form_payload"].keys() if "day" in key][0]

            data["form_payload"][year_key] = date_parts[0]
            data["form_payload"][month_key] = date_parts[1]
            data["form_payload"][day_key] = date_parts[2]


class AskAmount(BaseHandler):
    async def __call__(self, callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        await callback.message.delete()

        msg = await callback.message.reply("💵What is an amount paid?",
                                           reply=False,
                                           disable_notification=True)
        async with state.proxy() as data:
            data['init_instruction'] = msg["message_id"]
            if not data.get('form_payload'):
                data['form_payload'] = get_default_form_payload(self.config.get("form_payload_template"))

            category_key = [key for key in data["form_payload"].keys()
                            if key in self.config.get("form_payload_template").get("category").keys()
                            and "category" in self.config.get("form_payload_template").get("category")[key]][0]
            data['form_payload'][category_key] = callback.data

        await self.state.entering_amount.set()


class ParseAmount(BaseHandler):
    async def __call__(self, message: types.Message, state: FSMContext):
        async with state.proxy() as data:
            init_msg_to_delete = data.get('init_instruction')

        await message.delete()
        await self.bot.delete_message(chat_id=message.chat.id,
                                      message_id=init_msg_to_delete)

        if not re.match(r"\d+([.,]\d+)?", message.text):
            msg = await message.reply(text=f"⛔️Wrong format for spending amount.\n"
                                           f"🔤Should contain only numbers possibly with . or , decimal separator:",
                                      reply=False,
                                      disable_notification=True)
            async with state.proxy() as data:
                data['init_instruction'] = msg["message_id"]
            return

        msg = await message.reply(text=f"🔤Choose any comment to add or choose 'Custom comment' and write custom one:",
                                  reply_markup=build_listlike_keyboard(self.config.get("comments")),
                                  reply=False,
                                  disable_notification=True)
        async with state.proxy() as data:
            data['init_instruction'] = msg["message_id"]
            if not data.get('form_payload'):
                data['form_payload'] = get_default_form_payload(self.config.get("form_payload_template"))

            amount_key = [key for key in data["form_payload"].keys() if data["form_payload"][key] == 1000][0]
            data['form_payload'][amount_key] = message.text


class InputComment(BaseHandler):
    async def __call__(self, callback: types.CallbackQuery, state: FSMContext):
        form_payload = ""

        if callback.data == "Custom comment":
            msg = await callback.message.reply("🔤Input your comment:",
                                               reply=False,
                                               disable_notification=True)
            await callback.message.delete()
            async with state.proxy() as data:
                data['init_instruction'] = msg["message_id"]
            await self.state.commenting.set()
        else:
            async with state.proxy() as data:
                comment_key = [key for key in data["form_payload"].keys()
                               if key in self.config.get("form_payload_template").get("comment").keys()][0]
                data['form_payload'][comment_key] = callback.data
                form_payload = data['form_payload']

            res = r.post(self.config.get("form_url"), data=form_payload)
            if res.status_code == 200:
                await callback.message.reply(text=f"✅Expense has been recorded!\n"
                                                  f"Recorded data: "
                                                  f"{json.dumps(form_payload, sort_keys=True, indent=4)}",
                                             disable_notification=True)
            else:
                await callback.message.reply(text=f"⛔️NOT recorded!\n"
                                                  f"Data to be recorded: "
                                                  f"{json.dumps(form_payload, sort_keys=True, indent=4)}",
                                             disable_notification=True)
            await callback.message.delete()
            await state.finish()


class ParseComment(BaseHandler):
    async def __call__(self, message: types.Message, state: FSMContext):
        async with state.proxy() as data:
            init_msg_to_delete = data.get('init_instruction')
        await self.bot.delete_message(chat_id=message.chat.id,
                                      message_id=init_msg_to_delete)

        async with state.proxy() as data:
            comment_key = [key for key in data["form_payload"].keys()
                           if key in self.config.get("form_payload_template").get("comment").keys()][0]
            data['form_payload'][comment_key] = message.text
            form_payload = data['form_payload']

        res = r.post(self.config.get("form_url"), data=form_payload)
        if res.status_code == 200:
            await message.reply(text=f"✅Expense has been recorded!\n"
                                     f"Recorded data: "
                                     f"{json.dumps(form_payload, sort_keys=True, indent=4)}",
                                disable_notification=True)
        else:
            await message.reply(text=f"⛔️NOT recorded!\n"
                                     f"Data to be recorded: "
                                     f"{json.dumps(form_payload, sort_keys=True, indent=4)}",
                                disable_notification=True)

        await message.delete()
        await state.finish()
