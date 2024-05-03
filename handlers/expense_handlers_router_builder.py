import time
import re

from aiogram import types, Router, F, Bot
from aiogram.filters import Command, or_f
from aiogram.fsm.context import FSMContext
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


class ExpenseHandlersRouterBuilder(AbstractRouterBuilder):
    def __init__(self):
        super().__init__()
        self.router = Router(name=self.__class__.__name__)

    def build_default_router(self):
        self.router.message.register(self.handler_add_expense_start,
                                     Command(*['add', 'shortcut']))

        self.router.message.register(self.handler_gen_msg,
                                     Command('edit'))
        self.router.callback_query.register(self.handler_set_editing_state,
                                            F.data.in_({"edit"}))
        self.router.callback_query.register(self.handler_edit_back,
                                            self.state.edit_mode,
                                            F.data.in_("back"))

        self.router.callback_query.register(self.handler_input_date,
                                            F.data.in_(
                                                {"today", "yesterday", "other_date"}
                                            ))
        self.router.message.register(self.handler_parse_other_date,
                                     or_f(self.state.other_date_input,
                                          self.state.shortcut,
                                          self.state.edit_mode))
        self.router.callback_query.register(self.handler_edit_date,
                                            F.data.in_({"edit_date"}))

        self.router.callback_query.register(self.handler_ask_amount,
                                            self.state.reading_expense_category)

        self.router.message.register(self.handler_parse_amount,
                                     self.state.entering_amount)
        self.router.message.register(self.handler_parse_comment,
                                     self.state.commenting)

        self.router.callback_query.register(self.handler_parse_shortcut,
                                            self.state.shortcut_parsing)

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
                if shortcuts:
                    await state.set_state(self.state.shortcut)
                else:
                    msg = await message.answer(interface_messages.WRONG_NO_SHORTCUTS,
                                               disable_notification=True)
                    time.sleep(2)
                    await msg.delete()
                    await message.delete()
                    return

        msg = await message.answer(interface_messages.ASK_EXPENSE_DATE,
                                   reply_markup=build_date_keyboard(),
                                   disable_notification=True)
        await self.save_init_instruction_msg_id(msg, state)
        await message.delete()

    async def handler_input_date(self, callback: types.CallbackQuery, state: FSMContext):
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
                    "when": when_value
                }
            })
            await self.__route_user_after_date_enter(callback, state)  # goes to the next step

            if await state.get_state() == self.state.edit_mode:
                await state.clear()
                return
        else:
            msg = await callback.message.reply(interface_messages.INPUT_DATE_FORMAT,
                                               reply=False,
                                               disable_notification=True)
            await self.save_init_instruction_msg_id(msg, state)

            if not await state.get_state():
                # start date parsing workflow
                await state.set_state(self.state.other_date_input)

            if await state.get_state() == self.state.edit_mode:
                return

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
        await state.update_data({
            "db_payload": {
                "when": message.text
            }
        })
        await self.__route_user_after_date_enter(message, state)  # goes to the next step

        if await state.get_state() == self.state.edit_mode:
            await state.clear()

        await message.delete()

    async def handler_gen_msg(self, message: types.Message, state: FSMContext):
        await message.reply("Message to start editing workflow.", reply_markup=build_edit_mode_main_keyboard())
        await message.delete()

    async def handler_set_editing_state(self, callback: types.CallbackQuery, state: FSMContext):
        await callback.message.edit_reply_markup(str(callback.message.message_id), build_edit_mode_keyboard())
        await state.update_data({
            "msg_under_edit": callback.message,
            "expense_id": callback.message.message_id
        })
        await state.set_state(self.state.edit_mode)

    async def handler_edit_date(self, callback: types.CallbackQuery, state: FSMContext):
        await callback.message.edit_reply_markup(str(callback.message.message_id), build_date_keyboard())

    async def handler_edit_back(self, callback: types.CallbackQuery, state: FSMContext):
        s = await state.get_data()
        msg = s.get("msg_under_edit")
        await callback.message.edit_reply_markup(str(msg.message_id), build_edit_mode_main_keyboard())
        await state.clear()

    async def handler_ask_amount(self, callback: types.CallbackQuery, state: FSMContext):
        """
        **Step 2. Save expense category and ask for expense amount**\n
        """
        await callback.answer()
        cur_state_data = await state.get_data()
        await state.update_data({"db_payload": {
            **cur_state_data["db_payload"],
            "category": callback.data
        }})
        with self.db.get_session() as db:
            amounts = db.query(UsersProperties.property_value).filter(
                UsersProperties.properties.has(Properties.property_name == "amounts"),
                UsersProperties.user_id == callback.from_user.id
            ).first()[0]
            category_amounts = amounts.get(callback.data, amounts["default"])
            await state.update_data({"cur_category_amounts": category_amounts})

        msg = await callback.message.reply(interface_messages.ASK_EXPENSE_AMOUNT,
                                           reply=False,
                                           reply_markup=build_reply_keyboard(
                                               entities=category_amounts,
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
        cur_state_data = await state.get_data()

        if not await self.is_valid_expense_amount(message.text):
            msg = await message.reply(text=interface_messages.WRONG_EXPENSE_AMOUNT_FORMAT,
                                      reply=False,
                                      reply_markup=build_reply_keyboard(
                                          entities=cur_state_data["cur_category_amounts"],
                                          max_items_in_a_row=5),
                                      disable_notification=True)
            await self.save_init_instruction_msg_id(msg, state)
            return

        await state.set_state(self.state.commenting)
        await state.update_data({"db_payload": {
            **cur_state_data["db_payload"],
            "amount": message.text
        }})
        await self.__ask_for_expense_comment(message, state)  # go to the next step
        await message.delete()

    async def handler_parse_comment(self, message: types.Message, state: FSMContext, bot: Bot):
        """
        **Step 4. Save expense comment and send payload**\n
        """
        await self.delete_init_instruction(message.chat.id, state, bot)
        state_data = await state.get_data()
        expense_data = {
            "db_payload": {
                **state_data["db_payload"],
                "user_id": message.from_user.id,
                "comment": message.text
            }
        }
        state_data = await state.update_data(expense_data)
        try:
            with self.db.get_session() as db:
                expense_id = await self.add_expense_to_db(message, db, state_data)
                db.commit()
            expense_data["expense_id"] = expense_id
            await self.report_expense_details(
                message=message,
                expense_data=expense_data
            )
        except Exception as e:
            expense_data["expense_id"] = "No ID assigned"
            await self.report_expense_details(
                message=message,
                expense_data=expense_data,
                report_message=interface_messages.FAILED_RECORD,
                details=e
            )
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
        expense_data = {
                "db_payload": {
                    "when": cur_state_data["db_payload"]["when"],
                    "category": shortcut_payload["category"],
                    "amount": shortcut_payload["amount"],
                    "user_id": callback.from_user.id,
                    "comment": callback.data
                }
            }
        with self.db.get_session() as db:
            expense_id = await self.add_expense_to_db(callback.message, db, expense_data)
            db.commit()
        expense_data["expense_id"] = expense_id
        await self.report_expense_details(callback, expense_data)
        await self.delete_init_instruction(callback.message.chat.id, state, bot)
        await state.clear()

    async def __route_user_after_date_enter(self,
                                            message: types.Message | types.CallbackQuery,
                                            state: FSMContext):
        user_id = message.from_user.id
        message = message if isinstance(message, types.Message) \
            else message.message
        with self.db.get_session() as db:
            match await state.get_state():
                case self.state.shortcut.state:
                    reply_msg = interface_messages.ASK_SHORTCUT
                    shortcuts = db.query(UsersProperties.property_value) \
                        .filter(UsersProperties.properties.has(
                                    Properties.property_name == "shortcuts"),
                                UsersProperties.user_id == user_id
                        ).first()[0]
                    keyboard_layout = shortcuts.keys()
                    await state.update_data({"shortcuts_payloads": shortcuts})
                    await state.set_state(self.state.shortcut_parsing)
                case self.state.edit_mode:
                    await self.__edit_expense_attribute(state, ExpenseAttribute.DATE)
                    return
                case _:
                    reply_msg = interface_messages.ASK_EXPENSE_CATEGORY
                    keyboard_layout = db.query(UsersProperties.property_value) \
                        .filter(UsersProperties.properties.has(
                                    Properties.property_name == "categories"),
                                UsersProperties.user_id == user_id
                        ).first()[0]
                    await state.set_state(self.state.reading_expense_category)
        msg = await message.reply(reply_msg,
                                  reply_markup=build_listlike_keyboard(
                                      entities=keyboard_layout,
                                      max_items_in_a_row=3),
                                  reply=False,
                                  disable_notification=True)
        await self.save_init_instruction_msg_id(msg, state)

    async def __ask_for_expense_comment(self, message: types.Message, state: FSMContext):
        cur_state_data = await state.get_data()
        category = cur_state_data["db_payload"]["category"]
        with self.db.get_session() as db:
            comment_suggestions = db.query(UsersProperties.property_value).filter(
                UsersProperties.properties.has(Properties.property_name == "comments"),
                UsersProperties.user_id == message.from_user.id
            ).first()[0]
            comment_suggestions = comment_suggestions.get(category,
                                                          comment_suggestions["default"])

        reply_markup = build_reply_keyboard(
            entities=comment_suggestions,
            max_items_in_a_row=3) if comment_suggestions else None
        commenting_msg = interface_messages.ASK_COMMENT \
            if comment_suggestions else interface_messages.ASK_COMMENT_CUSTOM

        msg = await message.reply(text=commenting_msg,
                                  reply_markup=reply_markup,
                                  reply=False,
                                  disable_notification=True)
        await self.save_init_instruction_msg_id(msg, state)

    async def __edit_expense_attribute(self,
                                       state: FSMContext,
                                       attribute: str):
        editing_label = "(Edited)"
        s = await state.get_data()
        msg = s.get("msg_under_edit")
        edited_data = {"expense_id": re.search(r'(?<=ID: ).*$', msg.text, flags=re.M).group(0)}
        edited_text = msg.text

        try:
            with self.db.get_session() as db:
                match attribute:
                    case ExpenseAttribute.DATE:
                        attribute_value = s["db_payload"]["when"]
                        edited_data["spent_on"] = attribute_value
                        edited_text = re.sub(r'(?<=Date: ).*$',
                                             dt.strptime(attribute_value, '%Y-%m-%d').strftime("%B %d %Y (%A)"),
                                             edited_text,
                                             flags=re.M)
                    case _:
                        pass
                db.bulk_update_mappings(Expenses, [edited_data])
                db.commit()
        except Exception as e:
            editing_label = "(Editing failed, previous state remains)"
            self.logger.log("__edit_expense_attribute", msg.from_user.id, str(e), "error")

        await msg.edit_text(
            text=edited_text + (f"\n{editing_label}" if not msg.text.endswith("(Edited)") else ""),
            inline_message_id=str(msg.message_id),
            reply_markup=build_edit_mode_main_keyboard()
        )
