from abc import abstractmethod
import requests as r
import re
from datetime import datetime as dt
import json

from aiogram import types, Bot
from aiogram.fsm.context import FSMContext

from resources.states import States
from resources import interface_messages
from logger import Logger


class AbstractRouterBuilder:
    def __init__(self, config: dict):
        self.state = States
        self.logger = Logger()
        self.config = config
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
    async def is_valid_expense_amount(message: types.Message):
        if not re.match(r"^\d+([.,]\d+)?( USD|EUR|TRY|RUB|usd|eur|try|rub)?$", message.text):
            return False
        return True

    @staticmethod
    async def __fill_payload_field_date(field_key: str, value: str, state: FSMContext):
        date_parts = value.split("-")
        cur_state_data = await state.get_data()
        await state.update_data({
            "form_payload": {
                **cur_state_data["form_payload"],
                f"{field_key}_year": date_parts[0],
                f"{field_key}_month": date_parts[1],
                f"{field_key}_day": date_parts[2]
            }
        })

    @staticmethod
    async def __fill_payload_field_short_text(field_key: str, value: str | int, state: FSMContext):
        cur_state_data = await state.get_data()
        await state.update_data({"form_payload": {
            **cur_state_data["form_payload"],
            field_key: value
        }})

    @staticmethod
    async def __fill_payload_field_soft_single_choice(field_key: str, value: str, state: FSMContext):
        cur_state_data = await state.get_data()
        await state.update_data({
            "form_payload": {
                **cur_state_data["form_payload"],
                field_key: "__other_option__",
                f"{field_key}.other_option_response": value
            }
        })

    async def fill_payload_field(self, field_key: str, value: str | int, state: FSMContext):
        data = await state.get_data()
        if not data.get("form_payload"):
            await state.update_data({"form_payload": {}})
        field_properties = self.config.get("form_payload_mapping").get(field_key)
        match field_properties["type"]:
            case "date":
                await self.__fill_payload_field_date(field_properties["key"], value, state)
            case "soft_single_choice":
                await self.__fill_payload_field_soft_single_choice(field_properties["key"], value, state)
            case _:
                await self.__fill_payload_field_short_text(field_properties["key"], value, state)

    async def get_payload_field(self, field_key: str, state: FSMContext):
        field_properties = self.config.get("form_payload_mapping").get(field_key)
        data = await state.get_data()
        if not data.get("form_payload"):
            return
        match field_properties["type"]:
            case "date":
                return "-".join([data["form_payload"][f"{field_properties['key']}_year"],
                                 data["form_payload"][f"{field_properties['key']}_month"],
                                 data["form_payload"][f"{field_properties['key']}_day"]])
            case "soft_single_choice":
                return data["form_payload"][f"{field_properties['key']}.other_option_response"]
            case _:
                return data["form_payload"][f"{field_properties['key']}"]

    async def prettify_form_response(self, form_response: dict):
        prettified_response = {}
        self.logger.log(self, "", f"Original payload: {form_response}")
        mapping = self.config.get("form_payload_mapping")
        for key in mapping.keys():
            match mapping[key]["type"]:
                case "date":
                    prettified_response[key] = form_response.get(f"{mapping[key]['key']}_year") + '-' + \
                                               form_response.get(f"{mapping[key]['key']}_month") + '-' + \
                                               form_response.get(f"{mapping[key]['key']}_day")
                case "soft_single_choice":
                    prettified_response[key] = form_response.get(f"{mapping[key]['key']}.other_option_response")
                case _:
                    prettified_response[key] = form_response.get(mapping[key]["key"])
        return prettified_response

    async def send_form_response(self, chat_id: int, state: FSMContext, bot: Bot):
        data = await state.get_data()
        res = r.post(self.config.get("form_url"), data=data['form_payload'])
        form_payload = await self.prettify_form_response(data['form_payload'])

        if res.status_code == 200:
            await bot.send_message(chat_id=chat_id,
                                   text=interface_messages.SUCCESS_RECORD +
                                        f"{json.dumps(form_payload, sort_keys=True, indent=4)}",
                                   disable_notification=True)
        else:
            await bot.send_message(chat_id=chat_id,
                                   text=interface_messages.FAILED_RECORD +
                                        f"{json.dumps(form_payload, sort_keys=True, indent=4)}",
                                   disable_notification=True)

    @staticmethod
    async def convert_to_try(amount_with_currency: str):
        if any([cur in amount_with_currency.lower() for cur in ['usd', 'eur', 'rub']]):
            source_currency = amount_with_currency.split(' ')[1]
            res = r.get(url=f"https://cdn.jsdelivr.net/gh/fawazahmed0/currency-api@1/latest/currencies"
                            f"/{source_currency.lower()}"
                            f"/try.min.json")
            return round(float(amount_with_currency.split(' ')[0]) * res.json().get("try"), 2)
        return amount_with_currency
