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
    keyboards,
    bi_interface
)
from database.models import (
    Users,
    UsersProperties,
    Properties,
    Categories,
)


class SetupHandlersRouterBuilder(AbstractRouterBuilder):
    def __init__(self):
        super().__init__()
        self.router = Router(name=self.__class__.__name__)

    def build_default_router(self):
        self.router.message.register(self.handler_setup_init,
                                     Command(*['setup', 'reset']))

        self.router.message.register(self.handler_display_settings_menu,
                                     Command('settings'))

        self.router.callback_query.register(self.handler_set_categories,
                                            F.data == "categories")
        self.router.callback_query.register(self.handler_choosing_active_categories,
                                            self.state.settings_choosing_active_categories)

        self.router.callback_query.register(self.handler_choose_category,
                                            F.data.in_({"amounts", "comments"}))
        self.router.callback_query.register(self.handler_request_values_for_category,
                                            self.state.settings_request_values_for_category)
        self.router.message.register(self.handler_parse_values_for_category,
                                     self.state.settings_parse_values_for_category)

        self.router.callback_query.register(self.handler_choose_base_currency,
                                            F.data == "base_currency")
        self.router.callback_query.register(self.handler_set_base_currency,
                                            F.data.in_({"USD", "EUR", "TRY", "RUB"}))

        self.router.message.register(self.handler_setup_analytics,
                                     Command('analytics'))
        self.router.message.register(self.handler_reset_analytics,
                                     Command('reset_analytics'))

        self.router.callback_query.register(self.handler_ask_shortcut_category,
                                            F.data == "shortcuts")
        self.router.callback_query.register(self.handler_ask_shortcut_amount,
                                            self.state.settings_ask_shortcut_amount)
        self.router.message.register(self.handler_parse_shortcut_amount,
                                     self.state.settings_parse_shortcut_amount)
        self.router.message.register(self.handler_add_shortcut,
                                     self.state.settings_ask_shortcut_name)

        return self.router

    async def handler_setup_init(self, message: types.Message, inform: bool = True):
        # TODO: split flow for user to enable manual setup or automatic setup with default settings
        user_id = message.from_user.id
        command = message.text[1:]
        await message.delete()
        with self.db.get_session() as db:
            self.__create_user(db, user_id)
            if command == "setup":
                properties_to_set = self.__get_properties_to_setup(db, user_id)
                override = False
            else:
                properties_to_set = ["categories",
                                     "base_currency",
                                     "amounts",
                                     "comments"]
                override = True

            self.__setup_default_properties(db, properties_to_set, user_id, override)
            db.commit()

        if inform:
            information_text = interface_messages.DEFAULT_SETUP_SUCCESSFUL \
                if command == "setup" else interface_messages.RESET_SUCCESSFUL
            msg = await message.answer(text=information_text,
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
            self.__setup_default_property(db_session=db,
                                          user_id=callback.from_user.id,
                                          property_name="base_currency",
                                          property_value={"base_currency": callback.data},
                                          is_update=True)
            db.commit()

        await callback.answer(interface_messages.SETTINGS_SET_SUCCESS,
                                    disable_notification=True)
        await callback.message.delete()

    async def handler_set_categories(self, callback: types.CallbackQuery, state: FSMContext):
        with self.db.get_session() as db:
            chosen_categories = db.query(UsersProperties.property_value) \
                .filter(UsersProperties.properties.has(
                    Properties.property_name == "categories"
                ),
                UsersProperties.user_id == callback.from_user.id
            ).first()[0]
            categories = db.query(Categories.category_name).all()
            categories = [x[0] for x in categories]
        categories_map = {category: category in chosen_categories for category in categories}
        await state.update_data({"categories_setting": categories_map})
        msg = await callback.message.reply("Pick categories you would like to see while adding new expense:",
                                           reply_markup=keyboards.build_switchers_keyboard(categories_map),
                                           disable_notification=True)
        await callback.message.delete()
        await self.save_init_instruction_msg_id(msg, state)
        await state.set_state(self.state.settings_choosing_active_categories)

    async def handler_choosing_active_categories(self, callback: types.CallbackQuery, state: FSMContext, bot: Bot):
        cur_state_data = await state.get_data()
        categories_map = cur_state_data["categories_setting"]

        if not callback.data == "Confirm!":
            categories_map[callback.data] = not categories_map[callback.data]
            await state.update_data({"categories_setting": categories_map})
            await callback.message.edit_reply_markup(
                reply_markup=keyboards.build_switchers_keyboard(categories_map),
                disable_notification=True)
            return

        with self.db.get_session() as db:
            categories_prop = db.query(Properties) \
                .filter(Properties.property_name == "categories").first()
            db.bulk_update_mappings(UsersProperties, [{
                "user_id": callback.from_user.id,
                "property_id": categories_prop.property_id,
                "property_value": [cat for cat, is_active in categories_map.items() if is_active]
            }])
            db.commit()
        await callback.answer("✅ Categories set successfully!",
                              disable_notification=True)
        await self.delete_init_instruction(callback.from_user.id, state, bot)
        await state.clear()

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
        await state.set_state(self.state.settings_request_values_for_category)

    async def handler_request_values_for_category(self, callback: types.CallbackQuery, state: FSMContext):
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
                                           interface_messages.SETTINGS_REQUEST_VALUES_FOR_CATEGORY,
                                           disable_notification=True)
        await callback.message.delete()
        await self.save_init_instruction_msg_id(msg, state)
        await state.set_state(self.state.settings_parse_values_for_category)

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
            self.__setup_default_property(db_session=db,
                                          user_id=message.from_user.id,
                                          property_name=state_data["setting_property"],
                                          property_value=new_values,
                                          category=state_data["setting_property_category"],
                                          is_update=True)
            db.commit()

        msg = await message.answer(interface_messages.SETTINGS_SET_SUCCESS,
                                   disable_notification=True)
        await message.delete()
        time.sleep(2)
        await msg.delete()
        await state.clear()

    async def handler_setup_analytics(self, message: types.Message):
        superset = bi_interface.SuperSetInterface()
        if not await superset.is_user_exist(message.from_user.id):
            password = await superset.create_user_with_custom_role(message.from_user.id)
            await message.answer(f"User for Superset app created.\n\n"
                                 f"Superset dashboard available for you here: "
                                 f"{superset.superset_ui_url}\n\n"
                                 f"Your sign-in credentials:\n"
                                 f"Username: user_{message.from_user.id}\n"
                                 f"Password: {password}\n\n"
                                 f"You can change your password after login via "
                                 f"'Settings' in upper-right corner of the screen "
                                 f"-> 'Info' -> '🔒Reset My Password'.",
                                 disable_notification=True)
        else:
            await message.answer(f"User for Superset app was created earlier.\n\n"
                                 f"Superset dashboard available for you here: "
                                 f"{superset.superset_ui_url}\n\n"
                                 f"Your username: user_{message.from_user.id}\n",
                                 disable_notification=True)
        await message.delete()

    async def handler_reset_analytics(self, message: types.Message):
        superset = bi_interface.SuperSetInterface()
        password = await superset.reset_user(message.from_user.id)
        await message.answer(f"User for Superset app re-created.\n\n"
                             f"Superset dashboard available for you here: "
                             f"{superset.superset_ui_url}\n\n"
                             f"Your sign-in credentials:"
                             f"Username: user_{message.from_user.id}\n"
                             f"Password: {password}\n\n"
                             f"You can change your password after login via "
                             f"'Settings' in upper-right corner of the screen "
                             f"-> 'Info' -> '🔒Reset My Password'.",
                             disable_notification=True)
        await message.delete()

    async def handler_ask_shortcut_category(self, callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        with self.db.get_session() as db:
            reply_msg = interface_messages.ASK_EXPENSE_CATEGORY
            keyboard_layout = [x[0] for x in db.query(Categories.category_name).all()]
        msg = await callback.message.reply(reply_msg,
                                           reply_markup=keyboards.build_listlike_keyboard(
                                               entities=keyboard_layout,
                                               max_items_in_a_row=3),
                                           reply=False,
                                           disable_notification=True)
        await callback.message.delete()
        await self.save_init_instruction_msg_id(msg, state)
        await state.set_state(self.state.settings_ask_shortcut_amount)

    async def handler_ask_shortcut_amount(self, callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        await state.update_data({"shortcut_payload": {
            "category": callback.data
        }})
        msg = await callback.message.reply(interface_messages.ASK_EXPENSE_AMOUNT,
                                           reply=False,
                                           disable_notification=True)
        await callback.message.delete()
        await self.save_init_instruction_msg_id(msg, state)

        await state.set_state(self.state.settings_parse_shortcut_amount)

    async def handler_parse_shortcut_amount(self, message: types.Message, state: FSMContext, bot: Bot):
        await self.delete_init_instruction(message.chat.id, state, bot)
        cur_state_data = await state.get_data()

        if not await self.is_valid_expense_amount(message.text):
            msg = await message.reply(text=interface_messages.WRONG_EXPENSE_AMOUNT_FORMAT,
                                      reply=False,
                                      disable_notification=True)
            await message.delete()
            await self.save_init_instruction_msg_id(msg, state)
            return

        await state.update_data({"shortcut_payload": {
            **cur_state_data["shortcut_payload"],
            "amount": message.text
        }})
        msg = await message.reply(text="🔤 What will be the shortcut name?\n"
                                  "If you provide already existing name, it will be overwritten.",
                                  reply=False,
                                  disable_notification=True)
        await self.save_init_instruction_msg_id(msg, state)
        await message.delete()
        await state.set_state(self.state.settings_ask_shortcut_name)

    async def handler_add_shortcut(self, message: types.Message, state: FSMContext, bot: Bot):
        is_first_shortcut = False
        await self.delete_init_instruction(message.chat.id, state, bot)
        cur_state_data = await state.get_data()

        with self.db.get_session() as db:
            filters = [
                    UsersProperties.properties.has(Properties.property_name == "shortcuts"),
                    UsersProperties.user_id == message.from_user.id
                ]
            cur_prop_value = db.query(UsersProperties.property_value) \
                .filter(*filters).first()
            if cur_prop_value:
                cur_prop_value = cur_prop_value[0]
            else:
                cur_prop_value = {}
                is_first_shortcut = True
            cur_prop_value[message.text] = cur_state_data["shortcut_payload"]

            prop_id = db.query(Properties.property_id).filter(
                Properties.property_name == "shortcuts"
            ).first()[0]
            property_payload = {
                "user_id": message.from_user.id,
                "property_id": prop_id,
                "property_value": cur_prop_value
            }

            if is_first_shortcut:
                db.add(UsersProperties(**property_payload))
            else:
                db.bulk_update_mappings(UsersProperties, [property_payload])
            db.commit()
        msg = await message.answer(interface_messages.SETTINGS_SET_SUCCESS,
                                   disable_notification=True)
        await message.delete()
        time.sleep(2)
        await msg.delete()

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
        filters = [Properties.is_required == True]
        if existing_props:
            filters.append(Properties.property_id.notin_(existing_props))
        props = db_session.query(Properties.property_name).filter(*filters).all()
        print(props)
        return [x[0] for x in props]

    def __setup_default_properties(self,
                                   db_session: Session,
                                   properties_to_set: list[str],
                                   user_id: int,
                                   is_update: bool = False):
        for prop in properties_to_set:
            match prop:
                case "categories":
                    self.__setup_default_property(db_session, user_id, prop, [
                        "Fun", "Clothes", "Transportation", "Eat outside",
                        "Food", "Facilities", "Medicine", "Home", "Other", "Rent"
                    ], is_update=is_update)
                case "base_currency":
                    self.__setup_default_property(db_session, user_id, prop, {
                        prop: "USD"
                    }, is_update=is_update)
                case "amounts":
                    self.__setup_default_property(db_session, user_id, prop, {
                        "default": [1, 3, 5, 7, 10, 15, 25, 30],
                        "Transportation": [5, 15, 20, 30, 50],
                        "Eat outside": [10, 15, 20, 25, 30, 40, 50, 60]
                    }, is_update=is_update)
                case "comments":
                    self.__setup_default_property(db_session, user_id, prop, {
                        "default": ["Groceries", "Weekly groceries", "Cafe", "Restaurant",
                                    "MyFavoriteDoner", "Taxi", "Public transport", "Water",
                                    "Electricity", "Heating", "Internet"]
                    }, is_update=is_update)
                case _:
                    pass

    @staticmethod
    def __setup_default_property(db_session: Session,
                                 user_id: int,
                                 property_name: str,
                                 property_value: dict | list | None,
                                 category: str | None = None,
                                 is_update: bool = False):
        categories_prop = db_session.query(Properties) \
            .filter(Properties.property_name == property_name).first()
        if is_update:
            if category:
                filters = [
                    UsersProperties.properties.has(Properties.property_name == property_name),
                    UsersProperties.user_id == user_id
                ]
                current_prop_value = db_session.query(UsersProperties.property_value) \
                    .filter(*filters).first()[0]
                current_prop_value[category] = property_value
                property_value = current_prop_value
            db_session.bulk_update_mappings(UsersProperties, [{
                "user_id": user_id,
                "property_id": categories_prop.property_id,
                "property_value": property_value
            }])
            db_session.commit()
        else:
            db_session.add(UsersProperties(
                property_id=categories_prop.property_id,
                user_id=user_id,
                property_value=property_value
            ))
