from abc import abstractmethod
from aiogram import Bot, types
from aiogram.dispatcher import FSMContext
import requests as r
import json

from resources.states import States
from logger import Logger


class BaseHandler:
    def __init__(self, bot: Bot, states: States, logger: Logger, config: dict):
        self.bot = bot
        self.state = states
        self.logger = logger
        self.config = config

    @abstractmethod
    async def __call__(self, *args, **kwargs):
        pass

    @staticmethod
    async def save_init_instruction_msg_id(msg: types.Message, state: FSMContext):
        async with state.proxy() as data:
            data['init_instruction'] = msg.message_id

    async def delete_init_instruction(self, chat_id: int, state: FSMContext):
        async with state.proxy() as data:
            init_msg_id = data['init_instruction']
        await self.bot.delete_message(chat_id=chat_id, message_id=init_msg_id)

    @staticmethod
    async def __fill_payload_field_date(field_key: str, value: str, state: FSMContext):
        date_parts = value.split("-")
        async with state.proxy() as data:
            data["form_payload"][f"{field_key}_year"] = date_parts[0]
            data["form_payload"][f"{field_key}_month"] = date_parts[1]
            data["form_payload"][f"{field_key}_day"] = date_parts[2]

    @staticmethod
    async def __fill_payload_field_short_text(field_key: str, value: str | int, state: FSMContext):
        async with state.proxy() as data:
            data["form_payload"][field_key] = value

    @staticmethod
    async def __fill_payload_field_soft_single_choice(field_key: str, value: str, state: FSMContext):
        async with state.proxy() as data:
            data["form_payload"][field_key] = "__other_option__"
            data["form_payload"][f"{field_key}.other_option_response"] = value

    async def fill_payload_field(self, field_key: str, value: str | int, state: FSMContext):
        async with state.proxy() as data:
            if not data.get("form_payload"):
                data["form_payload"] = {}
        field_properties = self.config.get("form_payload_mapping").get(field_key)
        match field_properties["type"]:
            case "date":
                await self.__fill_payload_field_date(field_properties["key"], value, state)
            case "soft_single_choice":
                await self.__fill_payload_field_soft_single_choice(field_properties["key"], value, state)
            case _:
                await self.__fill_payload_field_short_text(field_properties["key"], value, state)

    async def prettify_form_response(self, form_response: dict):
        prettified_response = {}
        self.logger.info(self, "", f"Original payload: {form_response}")
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

    async def send_form_response(self, chat_id: int, state: FSMContext):
        async with state.proxy() as data:
            res = r.post(self.config.get("form_url"), data=data['form_payload'])
            form_payload = await self.prettify_form_response(data['form_payload'])

        if res.status_code == 200:
            await self.bot.send_message(chat_id=chat_id,
                                        text=f"✅Expense has been recorded!\n"
                                             f"Recorded data: \n"
                                             f"{json.dumps(form_payload, sort_keys=True, indent=4)}",
                                        disable_notification=True)
        else:
            await self.bot.send_message(chat_id=chat_id,
                                        text=f"⛔️NOT recorded!\n"
                                             f"Data to be recorded: \n"
                                             f"{json.dumps(form_payload, sort_keys=True, indent=4)}",
                                        disable_notification=True)

    @staticmethod
    async def convert_to_try(amount_with_currency: str):
        if any([cur in amount_with_currency.lower() for cur in ['usd', 'eur']]):
            source_currency = amount_with_currency.split(' ')[1]
            res = r.get(url=f"https://cdn.jsdelivr.net/gh/fawazahmed0/currency-api@1/latest/currencies"
                            f"/{source_currency.lower()}"
                            f"/try.min.json")
            return round(float(amount_with_currency.split(' ')[0]) * res.json().get("try"), 2)
        return amount_with_currency
