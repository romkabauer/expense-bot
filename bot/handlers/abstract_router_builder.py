from abc import abstractmethod
import re
from datetime import datetime as dt
from uuid import uuid4

from aiogram import (
    types,
    Bot
)
from aiogram.fsm.context import FSMContext

from resources.states import States
from resources.currency_rate_extractor import CurrencyRateExtractor
from resources import interface_messages
from resources.editing_labels import EditingLabels
from resources.expense_attributes import ExpenseAttribute
from resources.keyboards import build_edit_mode_main_keyboard
from database.database import DatabaseFacade
from database.models import (
    Expenses,
    Categories,
    UsersProperties
)
from logger import Logger


class AbstractRouterBuilder:
    def __init__(self, logger: Logger):
        self.state = States
        self.logger = logger
        self.db = DatabaseFacade()
        self.router = None
        self.supported_base_currencies = ["USD", "EUR", "RUB", "TRY", "GEL", "RSD", "AMD"]
        self.currency_rate_extractor = CurrencyRateExtractor(self.supported_base_currencies)

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
        data = await state.get_data()
        init_msg_id = data.get('init_instruction')
        if init_msg_id:
            await bot.delete_message(chat_id=chat_id, message_id=init_msg_id)

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

    async def is_valid_time_format(self, message: types.Message, state: FSMContext, bot: Bot):
        is_valid = True
        if not re.match(r"([0-1][0-9]|2[0-3]):[0-5][0-9]", message.text.strip()):
            await self.delete_init_instruction(message.chat.id, state, bot)
            await state.update_data(invalid_time_format_msg=interface_messages.WRONG_TIME_FORMAT)
            is_valid = False
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

    async def __add_expense_to_db(self, expense_data: dict):
        if not expense_data["currency"]:
            expense_data["currency"] = await self.get_base_currency(expense_data["user_id"])
        self.logger.log(self, "", f"{expense_data}")
        rates = await self.get_rates_on_expense_date(expense_data["spent_on"], expense_data["currency"])
        payload = {
            "expense_id": expense_data["expense_id"],
            "user_id": expense_data["user_id"],
            "spent_on": expense_data["spent_on"],
            "amount": expense_data["amount"],
            "currency": expense_data["currency"],
            "rates": rates,
            "comment": expense_data["comment"],
        }
        try:
            with self.db.get_session() as db:
                payload["category_id"] = db.query(Categories.category_id) \
                        .filter(Categories.category_name == expense_data["category"]) \
                        .first()[0]
                db.add(Expenses(**payload))
                db.commit()
        except Exception as e:
            payload["error"] = str(e)
            self.logger.log(self, expense_data.get("message").from_user.id, str(payload))

        return payload

    async def __split_expense_amount(self, amount: str):
        """Splits expense amount to amount and currency code (if it is provided)."""
        amount_split = amount.split(" ")
        if len(amount_split) == 1:
            return (float(amount), None)
        return (float(amount_split[0]), amount_split[1].upper())

    async def __add_message_id_to_expense(self, expense_id: str, message_id: int):
        with self.db.get_session() as db:
            db.bulk_update_mappings(Expenses, [{
                "expense_id": expense_id,
                "message_id": message_id
            }])
            db.commit()

    async def report_expense_details(self, expense_data: dict):
        message: types.Message = expense_data.get("message")
        expense_date_formatted = dt.strptime(expense_data["spent_on"], '%Y-%m-%d') \
            .strftime("%B %d %Y (%A)")
        expense_data["expense_id"] = uuid4()
        expense_data["amount"], expense_data["currency"] = (
            await self.__split_expense_amount(str(expense_data["amount"])))

        payload = await self.__add_expense_to_db(expense_data)
        reporting_data = (f"    Date: {expense_date_formatted}\n"
                          f"    Category: {expense_data['category']}\n"
                          f"    Amount: {payload['amount']} {payload['currency']}\n"
                          f"    Comment: `{payload['comment']}`")
        if not payload.get("error"):
            report_msg = interface_messages.SUCCESS_RECORD + reporting_data
            reply_markup = build_edit_mode_main_keyboard()
        else:
            report_msg = interface_messages.FAILED_RECORD + reporting_data \
                + "\n" + str(payload.get("error"))
            reply_markup = None
        msg = await message.reply(text=report_msg,
                                  reply_markup=reply_markup,
                                  parse_mode="Markdown",
                                  disable_notification=True)

        if not payload.get("error"):
            await self.__add_message_id_to_expense(expense_data["expense_id"], msg.message_id)

    async def get_rates_on_expense_date(self, expense_date: str, currency: str):
        rates = self.currency_rate_extractor.extract_currency_rates(currency, expense_date)
        return {"base": currency, "rates": rates["rates"]}

    async def edit_expense_attribute(self,
                                     state: FSMContext,
                                     attribute: ExpenseAttribute):
        editing_label = EditingLabels.EDITED.value
        s = await state.get_data()
        msg: types.Message = s.get("msg_under_edit")
        edited_data = {}
        edited_text = msg.text
        comment = re.search(r'(?<=Comment: ).*$', edited_text, flags=re.M).group(0)
        edited_text = re.sub(r'(?<=Comment: ).*$', f"`{comment}`", edited_text, flags=re.M)

        try:
            with self.db.get_session() as db:
                self.logger.log(self, "", f"{s}")
                expense_id = db.query(Expenses.expense_id).filter(
                    Expenses.user_id == msg.chat.id,
                    Expenses.message_id == msg.message_id
                ).first()[0]
                edited_data, edited_text = await self.__update_expense_attributes(
                    db_session=db,
                    attribute=attribute,
                    state_data=s,
                    expense_id=expense_id,
                    edited_text=edited_text,
                    base_currency=await self.get_base_currency(msg.chat.id)
                )
                db.bulk_update_mappings(Expenses, [edited_data])
                db.commit()
        except Exception as e:
            editing_label = EditingLabels.EDIT_FAILED.value
            self.logger.log(self, str(msg.chat.id), str(e) + f" {msg}", "error")

        await msg.edit_text(
            text=(edited_text + f"\n{editing_label}"
                  if not any(msg.text.endswith(x.value) for x in EditingLabels)
                  else edited_text.replace(EditingLabels.EDITED.value, editing_label)
                                  .replace(EditingLabels.EDIT_FAILED.value, editing_label)
                                  .replace(EditingLabels.DELETION_FAILED.value, editing_label)),
            parse_mode="Markdown",
            inline_message_id=str(msg.message_id),
            reply_markup=build_edit_mode_main_keyboard()
        )

    async def __update_expense_attributes(self,
                                   db_session,
                                   attribute: ExpenseAttribute,
                                   state_data: dict,
                                   expense_id: dict,
                                   edited_text: str,
                                   base_currency: str):
        edited_data = { "expense_id": expense_id }
        match attribute:
            case ExpenseAttribute.DATE:
                attribute_value = state_data["db_payload"]["spent_on"]
                edited_data["rates"] = self.currency_rate_extractor.extract_currency_rates(
                    base_currency, attribute_value)
                edited_data["spent_on"] = attribute_value
                edited_text = re.sub(r'(?<=Date: ).*$',
                                     dt.strptime(attribute_value, '%Y-%m-%d').strftime("%B %d %Y (%A)"),
                                     edited_text,
                                     flags=re.M)
            case ExpenseAttribute.CATEGORY:
                attribute_value = state_data["db_payload"]["category"]
                edited_data["category_id"] = db_session.query(Categories.category_id) \
                    .filter(Categories.category_name == attribute_value) \
                    .first()[0]
                edited_text = re.sub(r'(?<=Category: ).*$', attribute_value, edited_text, flags=re.M)
            case ExpenseAttribute.AMOUNT:
                amount = state_data["db_payload"]["amount"].split(" ")
                edited_data["amount"] = amount[0]
                edited_data["currency"] = base_currency if len(amount) == 1 else amount[1].upper()
                edited_text = re.sub(r'(?<=Amount: ).*$',
                                     f"{edited_data['amount']} {edited_data['currency']}",
                                     edited_text,
                                     flags=re.M)
            case ExpenseAttribute.COMMENT:
                comment = state_data["db_payload"]["comment"]
                edited_data["comment"] = comment
                edited_text = re.sub(r'(?<=Comment: ).*$',
                                     f"`{edited_data['comment']}`",
                                     edited_text,
                                     flags=re.M)

        return edited_data, edited_text
