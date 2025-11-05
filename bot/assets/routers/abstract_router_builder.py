"""
Abstract router builder
"""
import re
from abc import abstractmethod
from datetime import datetime as dt

from aiogram import (
    types,
    Bot
)
from aiogram.fsm.context import FSMContext

from static import SUPPORTED_BASE_CURRENCIES
from static.states import States
from static.interface_messages import (
    SUCCESS_RECORD,
    FAILED_RECORD
)
from static.literals import (
    UILabels,
    UpsertStatus
)
from utils.messaging import (
    KBBuilder,
    escape_markdown
)
from utils.db import (
    CategoriesDbUtils,
    ExpenseUncommited
)
from database.database import DatabaseFacade
from logger import Logger


class AbstractRouterBuilder:
    """
    Abstract router class, extends aiogram.Router indirectly.
    Acts as a template for other routers in the module.
    """
    def __init__(self, logger: Logger):
        self.state = States
        self.logger = logger
        self.db = DatabaseFacade()
        self.router = None
        self.supported_base_currencies = SUPPORTED_BASE_CURRENCIES

    @abstractmethod
    def build_default_router(self):
        """Abstract method to implement by each Router separately"""
        raise NotImplementedError

    @staticmethod
    async def save_init_instruction_msg_id(msg: types.Message, state: FSMContext):
        """Saves init instruction msg reference to delete later in the dialogue.
        Helps to keep the chat nice and clean.

        Args:
            msg (types.Message): msg to register as init instruction
            state (FSMContext): dialogue state
        """
        await state.update_data({UILabels.INIT_INSTRUCTION.value: msg.message_id})

    @staticmethod
    async def delete_init_instruction(chat_id: int, state: FSMContext, bot: Bot):
        """Deletes init instructions if exists. Helps to keep the chat nice and clean.

        Args:
            chat_id (int): chat where to delete init instruction
            state (FSMContext): dialogue state
            bot (Bot): bot instance to call delete API
        """
        data = await state.get_data()
        init_msg_id = data.get(UILabels.INIT_INSTRUCTION.value)
        if init_msg_id:
            await bot.delete_message(chat_id=chat_id, message_id=init_msg_id)

    async def send_silent_reply(
        self,
        msg: types.CallbackQuery | types.Message,
        state: FSMContext,
        msg_text: str,
        kb: types.InlineKeyboardMarkup | types.ReplyKeyboardMarkup | None = None,
        is_msg_text_markdown: bool = False
    ) -> types.Message:
        """Sends reply to the user wtih disabled notifications for the reply message,
        saves reply msg id to the dialogue state as init instruction msg.

        Args:
            msg (types.CallbackQuery | types.Message): msg to reply
            state (FSMContext): dialogue state
            msg_text (str): reply text for user
            kb (types.InlineKeyboardMarkup | types.ReplyKeyboardMarkup | None, optional): 
            Optional kb for user to interact with. Defaults to None.

        Returns:
            Message: returns reply msg object
        """
        message = msg if isinstance(msg, types.Message) else msg.message
        msg_to_send = msg_text if is_msg_text_markdown else escape_markdown(msg_text, 2)
        msg = await message.reply(
                msg_to_send,
                reply_markup=kb,
                reply=False,
                parse_mode="MarkdownV2",
                disable_notification=True)
        await state.update_data({UILabels.INIT_INSTRUCTION.value: msg.message_id})
        return msg

    @staticmethod
    def parse_expense_amount_input(amount: str, return_as_is: bool = False):
        """Splits expense amount to amount and currency code (if it is provided)."""
        amount_split = amount.split(" ")
        if len(amount_split) == 1 \
            or (len(amount_split) == 2
                and amount_split[1].upper() not in SUPPORTED_BASE_CURRENCIES):
            return (float(amount), None) if not return_as_is else amount
        return (
            (float(amount_split[0]), amount_split[1].upper())
            if not return_as_is
            else amount_split[0] + " " + amount_split[1].upper()
        )

    async def report_expense_details(self, bot: Bot, expense_draft: ExpenseUncommited):
        """
        Generates expense report message.

        Upserts expense_draft to the database.

        Sends report message if new expense record, updates report message for existing one.

        Args:
        bot (Bot): Telegram bot instance used to send messages.
        expense_draft (ExpenseUncommited): Draft expense object containing expense details.
        """
        category_name = await CategoriesDbUtils(self.db, self.logger) \
            .get_category_by_id(expense_draft.category_id)

        with self.db.get_session() as db_session:
            reporting_data = (
                f"    Date: {escape_markdown(expense_draft.spent_on.strftime("%B %d %Y (%A)"), 2)}\n"
                f"    Category: {category_name.category_name}\n"
                f"    Amount: {escape_markdown(str(expense_draft.amount), 2)} {expense_draft.currency}\n"
                f"    Comment: `{escape_markdown(expense_draft.comment, 2)}`"
            )

            try:
                _, status = await expense_draft.upsert_to_db(db_session)
                if status == UpsertStatus.UPDATED:
                    await bot.edit_message_text(
                        text=SUCCESS_RECORD + reporting_data,
                        chat_id=expense_draft.user_id,
                        message_id=expense_draft.message_id,
                        reply_markup=KBBuilder().build_edit_mode_main_kb(),
                        parse_mode="MarkdownV2"
                    )
                    db_session.commit()
                    return
                msg = await bot.send_message(
                    chat_id=expense_draft.user_id,
                    text=SUCCESS_RECORD + reporting_data,
                    reply_markup=KBBuilder().build_edit_mode_main_kb(),
                    parse_mode="MarkdownV2",
                    disable_notification=True
                )
                db_session.commit()
                expense_draft.message_id = msg.message_id
                expense_draft.created_at = dt.now()
                await expense_draft.upsert_to_db(db_session)
                db_session.commit()
            except Exception as e:
                self.logger.log(
                    self,
                    user=expense_draft.user_id,
                    extra_text=str(expense_draft.to_dict()) + "\n\n" + str(e)
                )
                await bot.send_message(
                    chat_id=expense_draft.user_id,
                    text=(FAILED_RECORD
                        + reporting_data
                        + "\n\nPlease contact @romka\_bauer\."),
                    parse_mode="MarkdownV2",
                    disable_notification=True
                )
