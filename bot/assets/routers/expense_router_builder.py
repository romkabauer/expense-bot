from datetime import datetime as dt, timedelta as td

import asyncio
from aiogram import (
    Router,
    Bot,
    F,
)
from aiogram.types import (
    Message,
    CallbackQuery,
)
from aiogram.filters import Command, or_f
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from static.interface_messages import *
from static.literals import *
from utils.messaging import *
from utils.db import (
    UsersDbUtils,
    UsersPropertiesDbUtils,
    CategoriesDbUtils,
    ExpenseUncommited
)
from routers.abstract_router_builder import AbstractRouterBuilder
from logger import Logger


class ExpenseRouterBuilder(AbstractRouterBuilder):
    def __init__(self, logger: Logger):
        super().__init__(logger)
        self.router = Router(name=self.__class__.__name__)

    def build_default_router(self):
        self.router.message.register(self.handler_add_expense_start,
                                     Command('add'))
        self.router.message.register(self.handler_shortcut_expense_start,
                                     Command('shortcut'))

        # Input date
        self.router.callback_query.register(self.handler_parse_date,
                                            F.data.in_(
                                                {
                                                    UILabels.TODAY.value,
                                                    UILabels.YESTERDAY.value,
                                                    UILabels.ANOTHER_DATE.value
                                                }
                                            ))
        self.router.message.register(self.handler_parse_another_date,
                                     or_f(self.state.another_date_input,
                                          self.state.edit_date))
        # Input category
        self.router.callback_query.register(self.handler_parse_category,
                                            or_f(self.state.reading_expense_category,
                                                 self.state.edit_category),
                                            F.data.not_in({UILabels.BACK.value}))
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
                                            F.data.in_({UILabels.EDIT.value}))
        self.router.callback_query.register(self.handler_edit_date,
                                            self.state.edit_mode,
                                            F.data.in_({UILabels.EDIT_DATE.value}))
        self.router.callback_query.register(self.handler_edit_category,
                                            self.state.edit_mode,
                                            F.data.in_({UILabels.EDIT_CATEGORY.value}))
        self.router.callback_query.register(self.handler_edit_amount,
                                            self.state.edit_mode,
                                            F.data.in_({UILabels.EDIT_AMOUNT.value}))
        self.router.callback_query.register(self.handler_edit_comment,
                                            self.state.edit_mode,
                                            F.data.in_({UILabels.EDIT_COMMENT.value}))

        self.router.callback_query.register(self.handler_back_to_main,
                                            F.data.in_({UILabels.BACK.value,
                                                        UILabels.DELETE_ABORT.value}))

        self.router.callback_query.register(self.handler_set_deleting_state,
                                            F.data.in_({UILabels.DELETE.value}))
        self.router.callback_query.register(self.handler_delete_expense,
                                            F.data.in_({UILabels.DELETE_CONFIRM.value}))

        return self.router

    async def handler_add_expense_start(self, message: Message, state: FSMContext):
        """
        **Step 0. Input point for commands 'add' and 'shortcut'**
        """
        user_id = message.from_user.id

        await UsersDbUtils(self.db, self.logger).create_user_if_not_exist(user_id)
        await self.send_silent_reply(message, state, ASK_EXPENSE_DATE, KBBuilder().build_date_kb())
        await message.delete()

    async def handler_shortcut_expense_start(self, message: Message, state: FSMContext):
        user_id = message.from_user.id
        up_utils = UsersPropertiesDbUtils(self.db, self.logger)

        await UsersDbUtils(self.db, self.logger).create_user_if_not_exist(user_id)
        shortcuts = await up_utils.get_user_property(user_id, UserProperty.SHORTCUTS)
        if not shortcuts:
            msg = await message.answer(ERROR_NO_SHORTCUTS, disable_notification=True)
            await message.delete()
            await asyncio.sleep(5)
            await msg.delete()
            return
        await state.update_data({ShortcutLabels.SHORTCUT_PAYLOADS.value: shortcuts})
        await state.set_state(self.state.shortcut_parsing)
        await self.send_silent_reply(
            message,
            state,
            ASK_SHORTCUT,
            KBBuilder().set_buttons(shortcuts.keys()).inline()
        )
        await message.delete()

    async def handler_parse_date(self, callback: CallbackQuery, state: FSMContext, bot: Bot):
        """
        **Step 1. Input date of expense**\n
        If today or yesterday, goes to the next step.\n
        If other date, it starts date parsing workflow - `handler_parse_another_date`.
        """
        await callback.answer()
        user_id = callback.from_user.id
        expense_draft = await ExpenseUncommited(logger=self.logger) \
            .sync_by_associated_msg(self.db, callback.message)

        if callback.data in [UILabels.TODAY.value, UILabels.YESTERDAY.value]:
            spent_on = (dt.now().strftime('%Y-%m-%d')
                if callback.data == UILabels.TODAY.value
                else (dt.now() - td(1)).strftime('%Y-%m-%d'))
            expense_draft.spent_on = spent_on
            await expense_draft.sync_currency_rates(self.db)
            await state.update_data({UILabels.EXPENSE_DRAFT.value: expense_draft})
            if await state.get_state() == self.state.edit_date:
                await self.report_expense_details(bot, expense_draft)
                await state.clear()
                return
            await state.set_state(self.state.reading_expense_category)
            kb = KBBuilder().set_buttons(
                await UsersPropertiesDbUtils(self.db, self.logger).get_user_categories_map(user_id)
            ).inline()
            await self.send_silent_reply(callback, state, ASK_EXPENSE_CATEGORY, kb)
        else:
            await self.send_silent_reply(callback, state, ASK_EXPENSE_DATE_FORMAT_HINT)
            if await state.get_state() == self.state.edit_date:
                await state.update_data({UILabels.EXPENSE_DRAFT.value: expense_draft})
                return
            await state.set_state(self.state.another_date_input)

        await callback.message.delete()

    async def handler_parse_another_date(self, message: Message, state: FSMContext, bot: Bot):
        """
        **Step 1.1. Date parsing workflow**\n
        Checks input message for format validity and that it is not in the future,
        then goes to next step.
        """
        await self.delete_init_instruction(message.chat.id, state, bot)
        data = await state.get_data()
        expense_draft: ExpenseUncommited = data.get(
            UILabels.EXPENSE_DRAFT.value,
            ExpenseUncommited(logger=self.logger)
        )

        try:
            expense_draft.spent_on = message.text
            await expense_draft.sync_currency_rates(self.db)
        except ValueError:
            await self.send_silent_reply(message, state, ERROR_DATE_FORMAT + ASK_EXPENSE_DATE_FORMAT_HINT)
            await message.delete()
            return

        if await state.get_state() == self.state.edit_date:
            await self.report_expense_details(bot, expense_draft)
            await state.clear()
            await message.delete()
            return
        await state.set_state(self.state.reading_expense_category)
        await state.update_data({UILabels.EXPENSE_DRAFT.value: expense_draft})
        kb = KBBuilder().set_buttons(
            await UsersPropertiesDbUtils(self.db, self.logger).get_user_categories_map(message.from_user.id)
        ).inline()
        await self.send_silent_reply(message, state, ASK_EXPENSE_CATEGORY, kb)
        await message.delete()

    async def handler_parse_category(
        self,
        callback: CallbackQuery,
        state: FSMContext,
        bot: Bot
    ):
        """
        **Step 2. Save expense category and ask for expense amount**\n
        """
        await callback.answer()
        data = await state.get_data()
        expense_draft: ExpenseUncommited = data.get(
            UILabels.EXPENSE_DRAFT.value,
            ExpenseUncommited(logger=self.logger)
        )

        expense_draft.category_id = callback.data

        if await state.get_state() == self.state.edit_category:
            await self.report_expense_details(bot, expense_draft)
            await state.clear()
            return

        await self.__ask_for_expense_attribute_based_on_state(state, callback, callback.data)
        await state.set_state(self.state.entering_amount)
        await state.update_data({UILabels.EXPENSE_DRAFT.value: expense_draft})
        await callback.message.delete()

    async def handler_parse_amount(self, message: Message, state: FSMContext, bot: Bot):
        """
        **Step 3. Save expense amount and go to next step**\n
        """
        await self.delete_init_instruction(message.chat.id, state, bot)
        data = await state.get_data()
        expense_draft: ExpenseUncommited = data.get(
            UILabels.EXPENSE_DRAFT.value,
            ExpenseUncommited(logger=self.logger)
        )
        up_utils = UsersPropertiesDbUtils(self.db, self.logger)

        try:
            amount, currency = self.parse_expense_amount_input(message.text)
            expense_draft.amount = amount
            expense_draft.currency = (currency
                if currency
                else await up_utils.get_user_property(message.from_user.id, UserProperty.BASE_CURRENCY)
            )
            expense_draft.user_id = message.from_user.id
            await expense_draft.sync_currency_rates(self.db)
        except ValueError:
            cat_amounts = await up_utils.get_user_property(
                message.from_user.id,
                UserProperty.AMOUNTS,
                expense_draft.category_id
            )
            await self.send_silent_reply(
                message, state, ERROR_EXPENSE_AMOUNT_FORMAT, KBBuilder().set_buttons(
                    cat_amounts
                ).set_max_items_in_a_row(5).reply()
            )
            await message.delete()
            return

        if await state.get_state() == self.state.edit_amount:
            await self.report_expense_details(bot, expense_draft)
            await state.clear()
            await message.delete()
            return

        await self.__ask_for_expense_attribute_based_on_state(state, message, expense_draft.category_id)
        await state.set_state(self.state.commenting)
        await message.delete()

    async def handler_parse_comment(self, message: Message, state: FSMContext, bot: Bot):
        """
        **Step 4. Save expense comment and send payload**\n
        """
        await self.delete_init_instruction(message.chat.id, state, bot)
        data = await state.get_data()
        expense_draft: ExpenseUncommited = data.get(
            UILabels.EXPENSE_DRAFT.value,
            ExpenseUncommited(logger=self.logger)
        )
        expense_draft.comment = message.text
        expense_draft.user_id = message.from_user.id

        if not await state.get_state() == self.state.edit_comment:
            expense_draft.created_at = dt.now()

        await self.report_expense_details(bot, expense_draft)
        await state.clear()
        await message.delete()

    async def handler_parse_shortcut(
        self,
        callback: CallbackQuery,
        state: FSMContext,
        bot: Bot
    ):
        """
        **Shortcut steps**\n
        Gets all expense properties from config and send payload.
        """
        await self.delete_init_instruction(callback.message.chat.id, state, bot)
        data = await state.get_data()
        shortcut_payload = data[ShortcutLabels.SHORTCUT_PAYLOADS.value][callback.data]
        expense_draft = ExpenseUncommited(logger=self.logger)

        expense_draft.user_id = callback.from_user.id
        category = await CategoriesDbUtils(self.db, self.logger) \
            .get_category_by_name(shortcut_payload[ShortcutLabels.SHORTCUT_PAYLOAD_CATEGORY.value])
        expense_draft.category_id = category.category_id
        expense_draft.spent_on = dt.now().strftime('%Y-%m-%d')
        amount, currency = self.parse_expense_amount_input(
            shortcut_payload[ShortcutLabels.SHORTCUT_PAYLOAD_AMOUNT.value]
        )
        expense_draft.amount = amount
        expense_draft.currency = currency
        await expense_draft.sync_currency_rates(self.db)
        expense_draft.comment = callback.data
        expense_draft.created_at = dt.now()

        await self.report_expense_details(bot, expense_draft)
        await state.clear()

    async def handler_set_editing_state(self, callback: CallbackQuery, state: FSMContext):
        await callback.message.edit_reply_markup(
            str(callback.message.message_id),
            (KBBuilder()
                .set_buttons([
                    UILabels.EDIT_DATE.value,
                    UILabels.EDIT_CATEGORY.value,
                    UILabels.EDIT_AMOUNT.value,
                    UILabels.EDIT_COMMENT.value
                ])
                .set_max_items_in_a_row(2)
                .include_back()
                .inline()
            )
        )
        await state.set_state(self.state.edit_mode)

    async def handler_edit_date(self, callback: CallbackQuery, state: FSMContext):
        await state.set_state(self.state.edit_date)
        await callback.message.edit_reply_markup(
            str(callback.message.message_id),
            KBBuilder().include_back().build_date_kb()
        )

    async def handler_edit_category(self, callback: CallbackQuery, state: FSMContext):
        expense_draft = await ExpenseUncommited(logger=self.logger) \
            .sync_by_associated_msg(self.db, callback.message)

        await state.set_state(self.state.edit_category)
        await state.update_data({UILabels.EXPENSE_DRAFT.value: expense_draft})
        await callback.message.edit_reply_markup(
            str(callback.message.message_id),
            KBBuilder().set_buttons(
                await UsersPropertiesDbUtils(self.db, self.logger) \
                    .get_user_categories_map(callback.from_user.id)
            ).include_back().inline()
        )

    async def handler_edit_amount(self, callback: CallbackQuery, state: FSMContext):
        expense_draft = await ExpenseUncommited(logger=self.logger) \
            .sync_by_associated_msg(self.db, callback.message)

        await state.set_state(self.state.edit_amount)
        await state.update_data({UILabels.EXPENSE_DRAFT.value: expense_draft})
        await self.__ask_for_expense_attribute_based_on_state(
            state,
            callback,
            expense_draft.category_id
        )

    async def handler_edit_comment(self, callback: CallbackQuery, state: FSMContext):
        expense_draft = await ExpenseUncommited(logger=self.logger) \
            .sync_by_associated_msg(self.db, callback.message)

        await state.set_state(self.state.edit_comment)
        await state.update_data({UILabels.EXPENSE_DRAFT.value: expense_draft})
        await self.__ask_for_expense_attribute_based_on_state(
            state,
            callback,
            expense_draft.category_id
        )

    async def handler_set_deleting_state(self, callback: CallbackQuery, state: FSMContext):
        await callback.message.edit_reply_markup(
            str(callback.message.message_id),
            (KBBuilder()
                .set_buttons(
                    [UILabels.DELETE_CONFIRM.value, UILabels.DELETE_ABORT.value]
                )
                .inline())
        )
        await state.set_state(self.state.delete_mode)

    async def handler_delete_expense(self, callback: CallbackQuery, state: FSMContext):
        try:
            expense_draft = await ExpenseUncommited(self.logger) \
                .sync_by_associated_msg(self.db, callback.message)
            await expense_draft.delete_if_exists(self.db)
            await callback.message.delete()
        except Exception:
            await self.send_silent_reply(
                callback,
                state,
                ERROR_EXPENSE_DELETION_FAILED
            )
            await callback.message.edit_reply_markup(
                str(callback.message.message_id),
                KBBuilder().build_edit_mode_main_kb()
            )
        await state.clear()

    async def handler_back_to_main(self, callback: CallbackQuery, state: FSMContext, bot: Bot):
        await self.delete_init_instruction(callback.message.chat.id, state, bot)
        await state.clear()
        try:
            await callback.message.edit_reply_markup(
                str(callback.message.message_id),
                KBBuilder().build_edit_mode_main_kb()
            )
        except TelegramBadRequest:
            pass

    async def __ask_for_expense_attribute_based_on_state(
        self,
        state: FSMContext,
        base_msg: CallbackQuery | Message,
        category_id: str = None
    ):
        if not category_id:
            category_id = "default"
        reply_msg = ASK_EXPENSE_AMOUNT
        reply_markup_suggestions = UserProperty.AMOUNTS

        if await state.get_state() == self.state.entering_amount:
            reply_msg = ASK_COMMENT
            reply_markup_suggestions = UserProperty.COMMENTS

        if await state.get_state() == self.state.edit_comment:
            reply_msg = HINT_COPY_COMMENT + ASK_COMMENT
            reply_markup_suggestions = UserProperty.COMMENTS

        category_suggestions = await UsersPropertiesDbUtils(self.db, self.logger) \
            .get_user_property(base_msg.from_user.id, reply_markup_suggestions, category_id)
        await self.send_silent_reply(
            base_msg,
            state,
            reply_msg,
            KBBuilder().set_buttons(category_suggestions).reply()
        )
