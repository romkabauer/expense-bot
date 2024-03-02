from aiogram import types, Router, F, Bot
from aiogram.filters import Command, or_f
from aiogram.fsm.context import FSMContext
from datetime import datetime as dt, timedelta as td

from handlers.abstract_router_builder import AbstractRouterBuilder
from resources.keyboards import build_date_keyboard, build_listlike_keyboard, build_reply_keyboard
from resources import interface_messages


class ExpenseHandlersRouterBuilder(AbstractRouterBuilder):
    def __init__(self, config: dict):
        super().__init__(config)
        self.router = Router(name=self.__class__.__name__)

    def build_default_router(self):
        self.router.message.register(self.handler_add_expense_start,
                                     Command(*['add', 'shortcut']))

        self.router.callback_query.register(self.handler_input_date,
                                            F.data.in_(
                                                {"today", "yesterday", "other_date"}
                                            ))
        self.router.message.register(self.handler_parse_other_date,
                                     or_f(self.state.other_date_input,
                                          self.state.shortcut))

        self.router.callback_query.register(self.handler_ask_amount,
                                            F.data.in_(
                                                set(self.config.get("spending_categories"))
                                            ))

        self.router.message.register(self.handler_parse_amount,
                                     self.state.entering_amount)
        self.router.message.register(self.handler_parse_comment,
                                     self.state.commenting)

        self.router.callback_query.register(self.handler_parse_shortcut,
                                            F.data.in_(
                                                set(self.config.get("shortcuts").keys())
                                            ))

        return self.router

    async def handler_add_expense_start(self, message: types.Message, state: FSMContext):
        """
        **Step 0. Input point for commands 'add' and 'shortcut'**
        """
        msg = await message.answer(interface_messages.ASK_EXPENSE_DATE,
                                   reply_markup=build_date_keyboard(),
                                   disable_notification=True)
        await self.save_init_instruction_msg_id(msg, state)
        if message.text == "/shortcut":
            await state.set_state(self.state.shortcut)
        await message.delete()

    async def handler_input_date(self, callback: types.CallbackQuery, state: FSMContext):
        """
        **Step 1. Input date of expense**\n
        If today or yesterday, goes to the next step.\n
        If other date, it starts date parsing workflow.
        """
        await callback.answer()

        if callback.data in ["today", "yesterday"]:
            when_value = dt.now().strftime('%Y-%m-%d') if callback.data == "today" \
                else (dt.now() - td(1)).strftime('%Y-%m-%d')
            await self.fill_payload_field(field_key="when", value=when_value, state=state)
            await self.__ask_expense_category(callback.message, state)  # goes to the next step
            await state.set_state(None)
        else:
            msg = await callback.message.reply(interface_messages.INPUT_DATE_FORMAT,
                                               reply=False,
                                               disable_notification=True)
            await self.save_init_instruction_msg_id(msg, state)
            # starts date parsing workflow
            await state.set_state(self.state.other_date_input) \
                if not await state.get_state() == self.state.shortcut.state else None

        await callback.message.delete()

    async def handler_parse_other_date(self, message: types.Message, state: FSMContext, bot: Bot):
        """
        **Step 1.1. Date parsing workflow**\n
        Checks input message for format validity and that it is not in the future,
        then goes to next step.
        """
        # keeping re-ask for date input if quality rules are not meet
        if not await self.is_valid_date_format(message, state, bot) or \
           not await self.is_valid_date_timeliness(message, state, bot):
            data = await state.get_data()
            text = (data.get("invalid_date_format_msg", "") +
                    data.get("invalid_date_timeliness_msg", "") +
                    interface_messages.INPUT_DATE_FORMAT)
            msg = await message.reply(text=text,
                                      reply=False,
                                      disable_notification=True)
            await self.save_init_instruction_msg_id(msg, state)
            await message.delete()
            return

        await self.delete_init_instruction(message.chat.id, state, bot)

        await self.__ask_expense_category(message, state)  # goes to the next step
        await self.fill_payload_field(field_key="when", value=message.text, state=state)
        await message.delete()

    async def handler_ask_amount(self, callback: types.CallbackQuery, state: FSMContext):
        """
        **Step 2. Save expense category and ask for expense amount**\n
        """
        await callback.answer()

        await self.fill_payload_field(field_key="category",
                                      value=callback.data,
                                      state=state)

        msg = await callback.message.reply(interface_messages.ASK_EXPENSE_AMOUNT,
                                           reply=False,
                                           reply_markup=build_reply_keyboard(
                                               entities=self.config.get("amounts"),
                                               max_items_in_a_row=5),
                                           disable_notification=True)
        await callback.message.delete()
        await self.save_init_instruction_msg_id(msg, state)

        await state.set_state(self.state.entering_amount)

    async def handler_parse_amount(self, message: types.Message, state: FSMContext, bot: Bot):
        """
        **Step 3. Save expense amount and go to next step**\n
        """
        await self.delete_init_instruction(message.chat.id, state, bot)

        if not await self.is_valid_expense_amount(message):
            msg = await message.reply(text=interface_messages.WRONG_EXPENSE_AMOUNT_FORMAT,
                                      reply=False,
                                      reply_markup=build_reply_keyboard(
                                          entities=self.config.get("amounts"),
                                          max_items_in_a_row=5),
                                      disable_notification=True)
            await self.save_init_instruction_msg_id(msg, state)
            return

        await state.set_state(self.state.commenting)
        await self.__ask_for_expense_comment(message, state)  # go to the next step

        await self.fill_payload_field(field_key="amount",
                                      value=await self.convert_to_try(message.text),
                                      state=state)
        await message.delete()

    async def handler_parse_comment(self, message: types.Message, state: FSMContext, bot: Bot):
        """
        **Step 4. Save expense comment and send payload**\n
        """
        await self.delete_init_instruction(message.chat.id, state, bot)
        await self.fill_payload_field(field_key="comment", value=message.text, state=state)
        await self.send_form_response(message.chat.id, state, bot)
        await message.delete()
        await state.clear()

    async def handler_parse_shortcut(self, callback: types.CallbackQuery, state: FSMContext, bot: Bot):
        """
        **Shortcut steps**\n
        Gets all expense properties from config and send payload.
        """
        self.logger.log(self, callback.from_user.id, str(await state.get_data()))
        await self.delete_init_instruction(callback.message.chat.id, state, bot)

        shortcut_payload = self.config.get("shortcuts")[callback.data]
        await self.fill_payload_field(field_key="when",
                                      value=await self.get_payload_field("when", state),
                                      state=state)
        await self.fill_payload_field(field_key="amount",
                                      value=shortcut_payload["amount"],
                                      state=state)
        await self.fill_payload_field(field_key="category",
                                      value=shortcut_payload["category"],
                                      state=state)
        await self.fill_payload_field(field_key="comment", value=callback.data, state=state)
        await self.send_form_response(callback.message.chat.id, state, bot)
        await state.clear()

    async def __ask_expense_category(self, message: types.Message, state: FSMContext):
        match await state.get_state():
            case self.state.shortcut.state:
                reply_msg = interface_messages.ASK_SHORTCUT
                keyboard_layout = self.config.get("shortcuts").keys()
            case _:
                reply_msg = interface_messages.ASK_EXPENSE_CATEGORY
                keyboard_layout = self.config.get("spending_categories")
        msg = await message.reply(reply_msg,
                                  reply_markup=build_listlike_keyboard(
                                      entities=keyboard_layout,
                                      max_items_in_a_row=3),
                                  reply=False,
                                  disable_notification=True)
        await self.save_init_instruction_msg_id(msg, state)

    async def __ask_for_expense_comment(self, message: types.Message, state: FSMContext):
        comment_suggestions = self.config.get("comments").get(
            await self.get_payload_field(field_key="category", state=state)
        )

        reply_markup = build_reply_keyboard(
            entities=comment_suggestions,
            max_items_in_a_row=3) if comment_suggestions else None
        commenting_msg = interface_messages.ASK_COMMENT \
            if comment_suggestions else interface_messages.ASK_COMMENT_CUSTOM

        msg = await message.reply(text=commenting_msg, reply_markup=reply_markup,
                                  reply=False,
                                  disable_notification=True)
        await self.save_init_instruction_msg_id(msg, state)
