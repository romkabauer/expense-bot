import time

from aiogram import (
    types,
    Router,
    Bot,
    F
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import Session

from handlers.abstract_router_builder import AbstractRouterBuilder
from resources import (
    interface_messages,
    keyboards
)
from database.models import (
    Users,
    UsersProperties,
    Properties,
)


class SetupHandlersRouterBuilder(AbstractRouterBuilder):
    def __init__(self):
        super().__init__()
        self.router = Router(name=self.__class__.__name__)

    def build_default_router(self):
        self.router.message.register(self.handler_setup_init,
                                     Command('setup'))

        self.router.message.register(self.handler_display_settings_menu,
                                     Command('settings'))

        self.router.callback_query.register(self.handler_set_categories,
                                            F.data == "categories")

        self.router.callback_query.register(self.handler_choose_category,
                                            F.data.in_({"amounts", "comments"}))
        self.router.callback_query.register(self.handler_ask_for_values_for_category,
                                            self.state.ask_values_for_category)
        self.router.message.register(self.handler_parse_values_for_category,
                                     self.state.setting_values_for_category)

        self.router.callback_query.register(self.handler_choose_base_currency,
                                            F.data == "base_currency")
        self.router.callback_query.register(self.handler_set_base_currency,
                                            F.data.in_({"USD", "EUR", "TRY", "RUB"}))

        self.router.callback_query.register(self.handler_not_implemented,
                                            F.data == "shortcuts")
        return self.router

    async def handler_setup_init(self, message: types.Message, inform: bool = True):
        # TODO: split flow for user to enable manual setup or automatic setup with default settings
        user_id = message.from_user.id
        await message.delete()
        with self.db.get_session() as db:
            self.__create_user(db, user_id)

            for prop in self.__get_properties_to_setup(db, user_id):
                match prop:
                    case "categories":
                        self.__setup_default_property(db, user_id, prop, [
                            "Fun", "Clothes", "Transportation", "Eat outside",
                            "Food", "Facilities", "Medicine", "Home", "Other"
                        ])
                    case "base_currency":
                        self.__setup_default_property(db, user_id, prop, {
                            prop: "USD"
                        })
                    case "amounts":
                        self.__setup_default_property(db, user_id, prop, {
                            "default": [1, 3, 5, 7, 10, 15, 25, 30],
                            "Transportation": [5, 15, 20, 30, 50],
                            "Eat outside": [10, 15, 20, 25, 30, 40, 50, 60]
                        })
                    case "comments":
                        self.__setup_default_property(db, user_id, prop, {
                            "default": ["Groceries", "Weekly groceries", "Cafe", "Restaurant",
                                        "MyFavoriteDoner", "Taxi", "Public transport", "Water",
                                        "Electricity", "Heating", "Internet"]
                        })
                    case _:
                        pass
            db.commit()

        if inform:
            msg = await message.answer(text=interface_messages.DEFAULT_SETUP_SUCCESSFUL,
                                       disable_notification=True)
            time.sleep(5)
            await msg.delete()

    async def handler_display_settings_menu(self, message: types.Message, state: FSMContext):
        with self.db.get_session() as db:
            user = db.query(Users).filter(Users.user_id == message.from_user.id).all()
            if not user:
                await self.handler_setup_init(message, inform=False)
            props = [p[0] for p in db.query(Properties.property_name).all()]

        msg = await message.answer(interface_messages.SETTINGS_START,
                                   reply_markup=keyboards.build_listlike_keyboard(props),
                                   disable_notification=True)
        await self.save_init_instruction_msg_id(msg, state)
        await message.delete()

    async def handler_choose_base_currency(self, callback: types.CallbackQuery, state: FSMContext):
        with self.db.get_session() as db:
            current_base_currency = await self.get_base_currency(callback.from_user.id)

        available_for_choosing = filter(
            lambda x: x != current_base_currency,
            ["USD", "EUR", "TRY", "RUB"]
        )
        msg = await callback.message.reply(f"Current base currency: {current_base_currency}.\n\n" +
                                           interface_messages.SETTINGS_BASE_CURRENCY_CHOICE,
                                           reply_markup=keyboards.build_listlike_keyboard(
                                               available_for_choosing,
                                               title_button_names=False
                                           ),
                                           disable_notification=True)
        await callback.message.delete()
        await self.save_init_instruction_msg_id(msg, state)

    async def handler_set_base_currency(self, callback: types.CallbackQuery, state: FSMContext):
        with self.db.get_session() as db:
            pid = db.query(Properties.property_id) \
                .filter(Properties.property_name == "base_currency").first()[0]
            db.bulk_update_mappings(UsersProperties, [{
                "user_id": callback.from_user.id,
                "property_id": pid,
                "property_value": {
                    "base_currency": callback.data
                }
            }])
            db.commit()

        msg = await callback.message.reply(interface_messages.SETTINGS_SET_SUCCESS,
                                           disable_notification=True)
        await callback.message.delete()
        time.sleep(2)
        await msg.delete()

    async def handler_set_categories(self, callback: types.CallbackQuery, state: FSMContext):
        msg = await callback.message.reply(interface_messages.SETTINGS_NOT_IMPLEMENTED +
                                           "\n\nChanges for category setting "
                                           "are expected in 1 month.",
                                           disable_notification=True)
        await callback.message.delete()
        time.sleep(3)
        await msg.delete()

    async def handler_choose_category(self, callback: types.CallbackQuery, state: FSMContext):
        await state.update_data({"setting_property": callback.data})
        with self.db.get_session() as db:
            categories = db.query(UsersProperties.property_value) \
                .filter(UsersProperties.properties.has(
                    Properties.property_name == "categories")
                ) \
                .first()
        msg = await callback.message.reply(interface_messages.SETTINGS_CATEGORIES_CHOICE,
                                           reply_markup=keyboards.build_listlike_keyboard(
                                               categories[0], additional_items=["default"]
                                           ),
                                           disable_notification=True)
        await callback.message.delete()
        await self.save_init_instruction_msg_id(msg, state)
        await state.set_state(self.state.ask_values_for_category)

    async def handler_ask_for_values_for_category(self, callback: types.CallbackQuery, state: FSMContext):
        state_data = await state.get_data()
        with self.db.get_session() as db:
            current_value = db.query(UsersProperties.property_value) \
                .filter(UsersProperties.properties.has(
                    Properties.property_name == state_data["setting_property"]
                ),
                UsersProperties.user_id == callback.from_user.id
            ).first()[0].get(callback.data, "no values set")
        await state.update_data({"setting_property_category": callback.data})

        msg = await callback.message.reply(f"Current values: {current_value}\n\n" +
                                           interface_messages.SETTINGS_ASK_FOR_VALUES_FOR_CATEGORY,
                                           disable_notification=True)
        await callback.message.delete()
        await self.save_init_instruction_msg_id(msg, state)
        await state.set_state(self.state.setting_values_for_category)

    async def handler_parse_values_for_category(self, message: types.Message, state: FSMContext, bot: Bot):
        await self.delete_init_instruction(message.chat.id, state, bot)
        state_data = await state.get_data()
        new_values = [v.strip() for v in message.text.split(",")]

        match state_data["setting_property"]:
            case "amounts":
                if not all([await self.is_valid_expense_amount(a)
                            for a in new_values]):
                    msg = await message.reply(text=interface_messages.WRONG_EXPENSE_AMOUNT_FORMAT,
                                              reply=False,
                                              disable_notification=True)
                    await self.save_init_instruction_msg_id(msg, state)
                    return
            case _:
                pass

        with self.db.get_session() as db:
            pid = db.query(Properties.property_id) \
                .filter(Properties.property_name == state_data["setting_property"]).first()[0]
            prop_value = db.query(UsersProperties.property_value) \
                .filter(UsersProperties.properties.has(
                            Properties.property_name == state_data["setting_property"]
                        ),
                        UsersProperties.user_id == message.from_user.id
                ).first()[0]
            prop_value[state_data["setting_property_category"]] = new_values
            db.bulk_update_mappings(UsersProperties, [{
                "user_id": message.from_user.id,
                "property_id": pid,
                "property_value": prop_value
            }])
            db.commit()

        msg = await message.answer(interface_messages.SETTINGS_SET_SUCCESS,
                                   disable_notification=True)
        await message.delete()
        time.sleep(2)
        await msg.delete()
        await state.clear()

    async def handler_not_implemented(self, callback: types.CallbackQuery, state: FSMContext):
        msg = await callback.message.answer(interface_messages.SETTINGS_NOT_IMPLEMENTED,
                                            disable_notification=True)
        await callback.message.delete()
        time.sleep(2)
        await msg.delete()

    @staticmethod
    def __create_user(db_session: Session, user_id: int):
        user = db_session.query(Users).filter(Users.user_id == user_id).all()
        if not user:
            db_session.add(Users(
                user_id=user_id,
                user_role="viewer"
            ))

    @staticmethod
    def __get_properties_to_setup(db_session: Session, user_id: int) -> list[str]:
        existing_props = db_session.query(UsersProperties.property_id) \
            .filter(UsersProperties.user_id == user_id).all()
        existing_props = [x[0] for x in existing_props]
        props = db_session.query(Properties.property_name) \
            .filter(
                Properties.property_id.notin_(existing_props),
                Properties.is_required is True
            ).all()
        return [x[0] for x in props]

    @staticmethod
    def __setup_default_property(db_session: Session,
                                 user_id: int,
                                 property_name: str,
                                 property_value: dict | list | None):
        categories_prop = db_session.query(Properties) \
            .filter(Properties.property_name == property_name).first()
        db_session.add(UsersProperties(
            property_id=categories_prop.property_id,
            user_id=user_id,
            property_value=property_value
        ))
