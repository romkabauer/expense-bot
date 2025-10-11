import asyncio
import re

from aiogram import types, Router, F, Bot
from aiogram.filters import Command, or_f
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from datetime import datetime as dt, timedelta as td

from handlers.abstract_router_builder import AbstractRouterBuilder
from database.models import (
    Expenses,
    Users,
    UsersProperties,
    Properties
)
from resources.keyboards import (
    build_date_keyboard,
    build_edit_mode_main_keyboard,
    build_edit_mode_keyboard,
    build_listlike_keyboard,
    build_reply_keyboard
)
from resources import interface_messages
from resources.expense_attributes import ExpenseAttribute
from resources.editing_labels import EditingLabels
from logger import Logger


class ExpenseHandlersRouterBuilder(AbstractRouterBuilder):
    def __init__(self, logger: Logger):
        super().__init__(logger)
        self.router = Router(name=self.__class__.__name__)

    def build_default_router(self):
        self.router.message.register(self.handler_add_expense_start,
                                     Command(*['add', 'shortcut']))

        # Input date
        self.router.callback_query.register(self.handler_parse_date,
                                            F.data.in_(
                                                {"today", "yesterday", "other_date"}
                                            ))
        self.router.message.register(self.handler_parse_other_date,
                                     or_f(self.state.other_date_input,
                                          self.state.shortcut,
                                          self.state.edit_date))
        # Input category
        self.router.callback_query.register(self.handler_parse_category,
                                            or_f(self.state.reading_expense_category,
                                                 self.state.edit_category),
                                            F.data.not_in({"back"}))
        # Input amount
        self.router.message.register(self.handler_parse_amount,
                                     or_f(self.state.entering_amount,
                                          self.state.edit_amount))
        # Input comment
        self.router.message.register(self.handler_parse_comment,
                                     or_f(self.state.commenting,
                                          self.state.edit_comment))

        # Shortcuts
        self.router.callback_query.register(self.handler_parse_shortcut,
                                            self.state.shortcut_parsing)

        # Editing / Deleting
        self.router.callback_query.register(self.handler_set_editing_state,
                                            F.data.in_({"edit"}))
        self.router.callback_query.register(self.handler_edit_date,
                                            self.state.edit_mode,
                                            F.data.in_({"edit_date"}))
        self.router.callback_query.register(self.handler_edit_category,
                                            self.state.edit_mode,
                                            F.data.in_({"edit_category"}))
        self.router.callback_query.register(self.handler_edit_amount,
                                            self.state.edit_mode,
                                            F.data.in_({"edit_amount"}))
        self.router.callback_query.register(self.handler_edit_comment,
                                            self.state.edit_mode,
                                            F.data.in_({"edit_comment"}))

        self.router.callback_query.register(self.handler_back_to_main,
                                            F.data.in_({"back", "cancel_deletion"}))

        self.router.callback_query.register(self.handler_set_deleting_state,
                                            F.data.in_({"delete"}))
        self.router.callback_query.register(self.handler_delete_expense,
                                            F.data.in_({"confirm_deletion"}))

        return self.router

    async def handler_add_expense_start(self, message: types.Message, state: FSMContext):
        """
        **Step 0. Input point for commands 'add' and 'shortcut'**
        """
        with self.db.get_session() as db:
            user = db.query(Users).filter(Users.user_id == message.from_user.id).all()
            if not user:
                msg = await message.answer(interface_messages.ERROR_ADD_BEFORE_SETUP,
                                           disable_notification=True)
                await self.save_init_instruction_msg_id(msg, state)
                await message.delete()
                return

            if message.text == "/shortcut":
                shortcuts = db.query(UsersProperties.property_value) \
                    .filter(UsersProperties.properties.has(
                        Properties.property_name == "shortcuts"),
                        UsersProperties.user_id == message.from_user.id
                    ).all()
                if not shortcuts:
                    msg = await message.answer(interface_messages.WRONG_NO_SHORTCUTS,
                                            disable_notification=True)
                    await message.delete()
                    await asyncio.sleep(2)
                    await msg.delete()
                    return
                await state.set_state(self.state.shortcut)
                await self.__route_user_by_state(message, state)
                await message.delete()
                return

        msg = await message.answer(interface_messages.ASK_EXPENSE_DATE,
                                   reply_markup=build_date_keyboard(),
                                   disable_notification=True)
        await self.save_init_instruction_msg_id(msg, state)
        await message.delete()

    async def handler_parse_date(self, callback: types.CallbackQuery, state: FSMContext):
        """
        **Step 1. Input date of expense**\n
        If today or yesterday, goes to the next step.\n
        If other date, it starts date parsing workflow - `handler_parse_other_date`.
        """
        await callback.answer()

        if callback.data in ["today", "yesterday"]:
            when_value = dt.now().strftime('%Y-%m-%d') if callback.data == "today" \
                else (dt.now() - td(1)).strftime('%Y-%m-%d')
            await state.update_data({
                "db_payload": {
                    "spent_on": when_value
                }
            })
            await self.__route_user_by_state(callback, state)

            if await state.get_state() == self.state.edit_date:
                await state.clear()
                return
        else:
            msg = await callback.message.reply(interface_messages.INPUT_DATE_FORMAT,
                                               reply=False,
                                               disable_notification=True)
            await self.save_init_instruction_msg_id(msg, state)

            if not await state.get_state():
                await state.set_state(self.state.other_date_input)

            if await state.get_state() == self.state.edit_date:
                return

        await callback.message.delete()

    async def handler_parse_other_date(self, message: types.Message, state: FSMContext, bot: Bot):
        """
        **Step 1.1. Date parsing workflow**\n
        Checks input message for format validity and that it is not in the future,
        then goes to next step.
        """
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
        await state.update_data({
            "db_payload": {
                "spent_on": message.text
            }
        })
        await self.__route_user_by_state(message, state)

        if await state.get_state() == self.state.edit_date:
            await state.clear()

        await message.delete()

    async def handler_parse_category(self, callback: types.CallbackQuery, state: FSMContext):
        """
        **Step 2. Save expense category and ask for expense amount**\n
        """
        await callback.answer()
        cur_state_data = await state.get_data()
        await state.update_data({"db_payload": {
            **cur_state_data.get("db_payload", {}),
            "category": callback.data
        }})

        if await state.get_state() == self.state.edit_category:
            await self.__route_user_by_state(callback, state)
            await state.clear()
            return

        msg = await self.__ask_for_expense_amount(callback.message,
                                                  state,
                                                  callback.from_user.id,
                                                  callback.data)

        await callback.message.delete()
        await self.save_init_instruction_msg_id(msg, state)

        await state.set_state(self.state.entering_amount)

    async def handler_parse_amount(self, message: types.Message, state: FSMContext, bot: Bot):
        """
        **Step 3. Save expense amount and go to next step**\n
        """
        await self.delete_init_instruction(message.chat.id, state, bot)
        cur_state_data = await state.get_data()

        if not await self.is_valid_expense_amount(message.text):
            msg = await message.reply(text=interface_messages.WRONG_EXPENSE_AMOUNT_FORMAT,
                                      reply=False,
                                      reply_markup=build_reply_keyboard(
                                          entities=cur_state_data["cur_category_amounts"],
                                          max_items_in_a_row=5),
                                      disable_notification=True)
            await self.save_init_instruction_msg_id(msg, state)
            await message.delete()
            return

        await state.update_data({"db_payload": {
            **cur_state_data.get("db_payload", {}),
            "amount": message.text
        }})

        if await state.get_state() == self.state.edit_amount:
            await self.__route_user_by_state(message, state)
            await message.delete()
            await state.clear()
            return

        await state.set_state(self.state.commenting)
        msg = await self.__ask_for_expense_comment(message, state, message.from_user.id, cur_state_data["db_payload"]["category"])
        await self.save_init_instruction_msg_id(msg, state)
        await message.delete()

    async def handler_parse_comment(self, message: types.Message, state: FSMContext, bot: Bot):
        """
        **Step 4. Save expense comment and send payload**\n
        """
        await self.delete_init_instruction(message.chat.id, state, bot)
        state_data = await state.get_data()
        expense_data = {
            "db_payload": {
                **state_data.get("db_payload", {}),
                "user_id": message.from_user.id,
                "message": message,
                "comment": message.text
            }
        }
        expense_data = await state.update_data(expense_data)

        if await state.get_state() == self.state.edit_comment:
            await self.__route_user_by_state(message, state)
        else:
            await self.report_expense_details(expense_data["db_payload"])

        await message.delete()
        await state.clear()

    async def handler_parse_shortcut(self, callback: types.CallbackQuery, state: FSMContext, bot: Bot):
        """
        **Shortcut steps**\n
        Gets all expense properties from config and send payload.
        """
        cur_state_data = await state.get_data()
        self.logger.log(self, callback.from_user.id, str(cur_state_data))

        shortcut_payload = cur_state_data["shortcuts_payloads"][callback.data]
        await self.report_expense_details({
            "spent_on": dt.now().strftime('%Y-%m-%d'),
            "category": shortcut_payload["category"],
            "amount": shortcut_payload["amount"],
            "user_id": callback.from_user.id,
            "message": callback.message,
            "comment": callback.data
        })
        await self.delete_init_instruction(callback.message.chat.id, state, bot)
        await state.clear()

    async def handler_set_editing_state(self, callback: types.CallbackQuery, state: FSMContext):
        await callback.message.edit_reply_markup(str(callback.message.message_id), build_edit_mode_keyboard())
        await state.update_data({"msg_under_edit": callback.message})
        await state.set_state(self.state.edit_mode)

    async def handler_edit_date(self, callback: types.CallbackQuery, state: FSMContext):
        await state.update_data({
            "editing_attribute": ExpenseAttribute.DATE
        })
        await state.set_state(self.state.edit_date)
        await callback.message.edit_reply_markup(
            str(callback.message.message_id),
            build_date_keyboard(include_back_button=True)
        )

    async def handler_edit_category(self, callback: types.CallbackQuery, state: FSMContext):
        await state.update_data({
            "editing_attribute": ExpenseAttribute.CATEGORY
        })
        await state.set_state(self.state.edit_category)
        await callback.message.edit_reply_markup(
            str(callback.message.message_id),
            build_listlike_keyboard(entities=await self.__get_user_property(callback.from_user.id,
                                                                            "categories"),
                                    additional_items=["back"],
                                    max_items_in_a_row=3)
        )

    async def handler_edit_amount(self, callback: types.CallbackQuery, state: FSMContext):
        await state.update_data({
            "editing_attribute": ExpenseAttribute.AMOUNT
        })
        await state.set_state(self.state.edit_amount)

        category = re.search(r'(?<=Category: ).*$', callback.message.text, flags=re.M).group(0)
        msg = await self.__ask_for_expense_amount(callback.message, state, callback.message.chat.id, category)
        await self.save_init_instruction_msg_id(msg, state)

    async def handler_edit_comment(self, callback: types.CallbackQuery, state: FSMContext):
        await state.update_data({
            "editing_attribute": ExpenseAttribute.COMMENT
        })

        await state.set_state(self.state.edit_comment)

        category = re.search(r'(?<=Category: ).*$', callback.message.text, flags=re.M).group(0)
        msg = await self.__ask_for_expense_comment(callback.message, state, callback.message.chat.id, category)
        await self.save_init_instruction_msg_id(msg, state)

    async def handler_set_deleting_state(self, callback: types.CallbackQuery, state: FSMContext):
        await callback.message.edit_reply_markup(str(callback.message.message_id), build_listlike_keyboard(
            ["confirm_deletion", "cancel_deletion"], title_button_names=True
        ))
        await state.update_data({"msg_under_edit": callback.message})
        await state.set_state(self.state.delete_mode)

    async def handler_delete_expense(self, callback: types.CallbackQuery, state: FSMContext):
        is_success = await self.__delete_expense(state)
        if is_success:
            await callback.message.delete()

    async def handler_back_to_main(self, callback: types.CallbackQuery, state: FSMContext, bot: Bot):
        await self.delete_init_instruction(callback.message.chat.id, state, bot)
        await state.clear()
        try:
            await callback.message.edit_reply_markup(str(callback.message.message_id),
                                                     build_edit_mode_main_keyboard())
        except TelegramBadRequest:
            pass

    async def __route_user_by_state(self,
                                    message: types.Message | types.CallbackQuery,
                                    state: FSMContext):
        user_id = message.from_user.id
        message = message if isinstance(message, types.Message) \
            else message.message
        match await state.get_state():
            case self.state.shortcut.state:
                reply_msg = interface_messages.ASK_SHORTCUT
                shortcuts = await self.__get_user_property(user_id, "shortcuts")
                keyboard_layout = shortcuts.keys()
                await state.update_data({"shortcuts_payloads": shortcuts})
                await state.set_state(self.state.shortcut_parsing)
            case self.state.edit_date | self.state.edit_category \
                 | self.state.edit_amount | self.state.edit_comment:
                s = await state.get_data()
                await self.edit_expense_attribute(state, s.get("editing_attribute"))
                return
            case _:
                reply_msg = interface_messages.ASK_EXPENSE_CATEGORY
                keyboard_layout = await self.__get_user_property(user_id, "categories")
                await state.set_state(self.state.reading_expense_category)
        msg = await message.reply(reply_msg,
                                  reply_markup=build_listlike_keyboard(
                                      entities=keyboard_layout,
                                      max_items_in_a_row=3),
                                  reply=False,
                                  disable_notification=True)
        await self.save_init_instruction_msg_id(msg, state)

    async def __ask_for_expense_comment(self,
                                        message: types.Message,
                                        state: FSMContext,
                                        user_id: int,
                                        category_name: str = "default"):
        comment_suggestions = await self.__get_user_property(user_id=user_id,
                                                             property_name="comments",
                                                             category_name=category_name)
        if comment_suggestions:
            reply_markup = build_reply_keyboard(entities=comment_suggestions, max_items_in_a_row=3)
            commenting_msg = interface_messages.ASK_COMMENT
        else:
            reply_markup, commenting_msg = None, interface_messages.ASK_COMMENT_CUSTOM

        if await state.get_state() == self.state.edit_comment:
            commenting_msg = "🔶You can copy current comment tapping on it.\n\n" \
                             + commenting_msg

        msg = await message.reply(text=commenting_msg,
                                  reply_markup=reply_markup,
                                  reply=False,
                                  disable_notification=True)
        return msg

    async def __ask_for_expense_amount(self,
                                       message: types.Message,
                                       state: FSMContext,
                                       user_id: int,
                                       category_name: str = "default"):
        category_amounts = await self.__get_user_property(user_id=user_id,
                                                          property_name="amounts",
                                                          category_name=category_name)
        await state.update_data({"cur_category_amounts": category_amounts})

        msg = await message.reply(interface_messages.ASK_EXPENSE_AMOUNT,
                                  reply=False,
                                  reply_markup=build_reply_keyboard(
                                      entities=category_amounts,
                                      max_items_in_a_row=5),
                                  disable_notification=True)
        return msg

    async def __delete_expense(self,
                               state: FSMContext) -> str:
        editing_label = EditingLabels.DELETION_FAILED.value
        s = await state.get_data()
        msg: types.Message = s.get("msg_under_edit")
        edited_text = msg.text
        try:
            with self.db.get_session() as db:
                expense_id = db.query(Expenses.expense_id).filter(
                    Expenses.user_id == msg.chat.id,
                    Expenses.message_id == msg.message_id
                ).first()[0]
                db.delete(db.query(Expenses).get(expense_id))
                db.commit()
            return "success"
        except Exception as e:
            self.logger.log("__delete_expense", msg.from_user.id, str(e), "error")
            await msg.edit_text(
                text=(edited_text + f"\n{editing_label}"
                      if not any(msg.text.endswith(x.value) for x in EditingLabels)
                      else edited_text
                      .replace(EditingLabels.EDITED.value, editing_label)
                      .replace(EditingLabels.EDIT_FAILED.value, editing_label)
                      .replace(EditingLabels.DELETION_FAILED.value, editing_label)),
                inline_message_id=str(msg.message_id),
                reply_markup=build_edit_mode_main_keyboard()
            )

    async def __get_user_property(self, user_id: int, property_name: str, category_name: str = None):
        with self.db.get_session() as db:
            property_value = db.query(UsersProperties.property_value).filter(
                UsersProperties.properties.has(Properties.property_name == property_name),
                UsersProperties.user_id == user_id
            ).first()[0]
            if category_name:
                return property_value.get(category_name, property_value["default"])
            return property_value
