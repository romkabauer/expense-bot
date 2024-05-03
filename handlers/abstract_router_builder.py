from abc import abstractmethod
from typing import Any
import re
from datetime import datetime as dt
from uuid import uuid4

from aiogram import (
    types,
    Bot
)
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import Session

from resources.states import States
from resources.currency_rate_extractor import CurrencyRateExtractor
from resources import interface_messages
from resources.keyboards import build_edit_mode_main_keyboard
from database.database import DatabaseFacade
from database.models import (
    Expenses,
    Categories,
    UsersProperties
)
from logger import Logger


class AbstractRouterBuilder:
    def __init__(self):
        self.state = States
        self.logger = Logger()
        self.db = DatabaseFacade()
        self.router = None
        self.supported_base_currencies = ["USD", "EUR", "RUB", "TRY", "GEL", "RSD", "AMD"]

    @abstractmethod
    def build_default_router(self):
        raise NotImplementedError

    def add_handler(self, handler_type: str, handler: callable, *filters):
        match handler_type:
            case "message":
                self.router.message.register(handler, *filters)
            case "callback":
                self.router.callback_query.register(handler, *filters)
            case _:
                self.router.message.register(handler, *filters)

    @staticmethod
    async def save_init_instruction_msg_id(msg: types.Message, state: FSMContext):
        await state.update_data({'init_instruction': msg.message_id})

    @staticmethod
    async def delete_init_instruction(chat_id: int, state: FSMContext, bot: Bot):
        init_msg_id = await state.get_data()
        await bot.delete_message(chat_id=chat_id, message_id=init_msg_id['init_instruction'])

    async def is_valid_date_format(self, message: types.Message, state: FSMContext, bot: Bot):
        is_valid = True
        if not re.match(r"20\d{2}-(1[0-2]|0[1-9])-(3[0-1]|1[0-9]|2[0-9]|0[1-9])", message.text):
            await self.delete_init_instruction(message.chat.id, state, bot)
            await state.update_data(invalid_date_format_msg=interface_messages.WRONG_DATE_FORMAT)
            return not is_valid
        data = await state.get_data()
        data.pop("invalid_date_format_msg", "")
        await state.set_data(data)
        return is_valid

    async def is_valid_date_timeliness(self, message: types.Message, state: FSMContext, bot: Bot):
        is_valid = True
        if dt.strptime(message.text, '%Y-%m-%d') > dt.now():
            await self.delete_init_instruction(message.chat.id, state, bot)
            await state.update_data(invalid_date_timeliness_msg=interface_messages.WRONG_DATE_TIMELINESS)
            return not is_valid
        data = await state.get_data()
        data.pop("invalid_date_timeliness_msg", "")
        await state.set_data(data)
        return is_valid

    async def is_valid_expense_amount(self, message: str):
        pattern = (r"^\d+([.]\d+)?(.("
                   f"{'|'.join([f'{x}|{x.lower()}' for x in self.supported_base_currencies])}"
                   r"))?$")
        if not re.match(pattern, message):
            return False
        return True

    async def get_base_currency(self, user_id):
        with self.db.get_session() as db:
            base_currency = db.query(UsersProperties.property_value) \
                .filter(UsersProperties.properties.has(property_name="base_currency"),
                        UsersProperties.users.has(user_id=user_id)) \
                .first()[0]
        return base_currency["base_currency"]

    async def add_expense_to_db(self, message: types.Message, db: Session, expense_data: dict):
        data = expense_data["db_payload"]
        user_id = data["user_id"]
        amount, currency, rates = await self.get_rates_on_expense_date(
            data["when"],
            data["amount"],
            user_id
        )
        expense_id = uuid4()
        db.add(Expenses(
            expense_id=expense_id,
            user_id=user_id,
            category_id=db.query(Categories.category_id)
                          .filter(Categories.category_name == data["category"])
                          .first()[0],
            spent_on=data["when"],
            amount=amount,
            currency=currency,
            rates=rates,
            comment=data["comment"],
        ))
        return expense_id

    async def report_expense_details(self,
                                     message: types.Message | types.CallbackQuery,
                                     expense_data: dict,
                                     report_message: str = interface_messages.SUCCESS_RECORD,
                                     details: Any = ""):
        if isinstance(message, types.Message):
            user_id, message = message.from_user.id, message
        else:
            user_id, message = message.from_user.id, message.message
        self.logger.log(self, str(message.from_user.id), str(expense_data))
        data = expense_data["db_payload"]
        amount = f"{data['amount']} {await self.get_base_currency(user_id)}" \
            if " " not in data['amount'] else f"{data['amount']}"
        expense_date_formatted = dt.strptime(data["when"], '%Y-%m-%d') \
            .strftime("%B %d %Y (%A)")
        await message.reply(text=report_message +
                                 f"    ID: {expense_data['expense_id']}\n"
                                 f"    Date: {expense_date_formatted}\n"
                                 f"    Category: {data['category']}\n"
                                 f"    Amount: {amount}\n"
                                 f"    Comment: {data['comment']}" +
                            str(details),
                            reply_markup=build_edit_mode_main_keyboard(),
                            parse_mode="Markdown",
                            disable_notification=True)

    async def get_rates_on_expense_date(self, when: str, amount_with_currency: str, user_id: int):
        base_currency = await self.get_base_currency(user_id)
        if base_currency not in self.supported_base_currencies:
            base_currency = "USD"

        rates = CurrencyRateExtractor(
            self.supported_base_currencies,
            base_currency,
            when
        ).extract_currency_rates()
        source_data = amount_with_currency.split(' ')

        if len(source_data) == 1:
            source_data.append(base_currency)

        return (float(source_data[0]),
                source_data[1].upper(),
                {"base": base_currency, "rates": rates["rates"]})
