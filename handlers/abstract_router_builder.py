from abc import abstractmethod
from typing import Any
import requests as r
import re
from datetime import datetime as dt

from aiogram import (
    types,
    Bot
)
from aiogram.fsm.context import FSMContext

from resources.states import States
from resources import interface_messages
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

    @staticmethod
    async def is_valid_expense_amount(message: str):
        if not re.match(r"^\d+([.]\d+)?(.(USD|EUR|TRY|GBP|usd|eur|try|gbp))?$", message):
            return False
        return True

    async def get_base_currency(self, user_id):
        with self.db.get_session() as db:
            base_currency = db.query(UsersProperties.property_value) \
                .filter(UsersProperties.properties.has(property_name="base_currency"),
                        UsersProperties.users.has(user_id=user_id)) \
                .first()[0]
        return base_currency["base_currency"]

    async def add_expense_to_db(self, message: types.Message, db, expense_data: dict):
        data = expense_data["db_payload"]
        user_id = data["user_id"]
        amount, currency, rates = await self.get_rates_on_expense_date(
            data["when"],
            data["amount"],
            user_id
        )
        db.add(Expenses(
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

    async def report_expense_details(self,
                                     message: types.Message,
                                     expense_data: dict,
                                     report_message: str = interface_messages.SUCCESS_RECORD,
                                     details: Any = ""):
        data = expense_data["db_payload"]
        expense_date_formatted = dt.strptime(data["when"], '%Y-%m-%d') \
            .strftime("%B %d %Y (%A)")
        await message.reply(text=report_message +
                                 f"    Date: {expense_date_formatted}\n"
                                 f"    Category: {data['category']}\n"
                                 f"    Amount: {data['amount']}\n"
                                 f"    Comment: {data['comment']}" +
                            str(details),
                            parse_mode="Markdown",
                            disable_notification=True)

    async def get_rates_on_expense_date(self, when: str, amount_with_currency: str, user_id: int):
        base_currency = await self.get_base_currency(user_id)
        params = {
            "base": base_currency,
            "date": when
        }

        res = r.get("https://api.vatcomply.com/rates", params=params)
        rates = res.json()

        if any([cur in amount_with_currency.upper() for cur in ['USD', 'EUR', 'RUB', 'TRY']]):
            source_data = amount_with_currency.split(' ')
            source_amount, source_currency = float(source_data[0]), source_data[1].upper()
            return (source_amount,
                    source_currency,
                    {"base": rates["base"], "rates": rates["rates"]})
        return (amount_with_currency,
                base_currency,
                {"base": base_currency, "rates": rates["rates"]})
