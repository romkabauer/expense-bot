import asyncio
from aiogram import (
    types,
    Router,
    Bot,
    F
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from routers.abstract_router_builder import AbstractRouterBuilder
from static.interface_messages import *
from static.literals import *
from utils.messaging import *
from utils.bi_interface import SupersetInterface
from utils.db import (
    UsersPropertiesDbUtils,
    UsersDbUtils,
    CategoriesDbUtils,
)
from logger import Logger


class SetupRouterBuilder(AbstractRouterBuilder):
    def __init__(self, logger: Logger):
        super().__init__(logger)
        self.router = Router(name=self.__class__.__name__)

    def build_default_router(self):
        self.router.message.register(self.handler_setup_init,
                                     Command(*['start', 'reset']))

        self.router.message.register(self.handler_display_settings_menu,
                                     Command('settings'))

        self.router.callback_query.register(self.handler_set_categories,
                                            F.data == UserProperty.CATEGORIES.value)
        self.router.callback_query.register(self.handler_choosing_active_categories,
                                            self.state.settings_choosing_active_categories)

        self.router.callback_query.register(self.handler_choose_category,
                                            F.data.in_({UserProperty.AMOUNTS.value,
                                                        UserProperty.COMMENTS.value}))
        self.router.callback_query.register(self.handler_request_values_for_category,
                                            self.state.settings_request_values_for_category)
        self.router.message.register(self.handler_parse_values_for_category,
                                     self.state.settings_parse_values_for_category)

        self.router.callback_query.register(self.handler_choose_base_currency,
                                            F.data == UserProperty.BASE_CURRENCY.value)
        self.router.callback_query.register(self.handler_set_base_currency,
                                            F.data.in_(self.supported_base_currencies))

        self.router.message.register(self.handler_setup_analytics,
                                     Command('analytics'))
        self.router.message.register(self.handler_reset_analytics,
                                     Command('reset_analytics'))

        self.router.callback_query.register(self.handler_manage_shortcuts,
                                            F.data == UserProperty.SHORTCUTS.value)
        self.router.callback_query.register(self.handler_ask_shortcut_category,
                                            F.data == UILabels.SETTINGS_SHORTCUTS_ADD_EDIT.value)
        self.router.callback_query.register(self.handler_parse_shortcut_category,
                                            self.state.settings_ask_shortcut_amount)
        self.router.message.register(self.handler_parse_shortcut_amount,
                                     self.state.settings_parse_shortcut_amount)
        self.router.message.register(self.handler_add_shortcut,
                                     self.state.settings_ask_shortcut_name)
        self.router.callback_query.register(self.handler_ask_shortcut_to_delete,
                                            F.data == UILabels.SETTINGS_SHORTCUTS_DELETE.value)
        self.router.callback_query.register(self.handler_delete_shortcut,
                                            self.state.settings_delete_shortcut)

        return self.router

    async def handler_setup_init(self, message: types.Message):
        user_id = message.from_user.id
        command = message.text[1:]
        await message.delete()

        await UsersDbUtils(self.db, self.logger).create_user_if_not_exist(user_id)
        info_text = SUCCESS_DEFAULT_SETUP

        if command == "reset":
            await UsersDbUtils(self.db, self.logger).reset_user_properties(user_id)
            info_text = SUCCESS_RESET

        await message.answer(text=info_text, disable_notification=True)

    async def handler_display_settings_menu(self, message: types.Message, state: FSMContext):
        user_utils = UsersDbUtils(self.db, self.logger)
        await user_utils.create_user_if_not_exist(message.from_user.id)

        await self.send_silent_reply(
            message,
            state,
            SETTINGS_START,
            KBBuilder().set_buttons(
                await UsersPropertiesDbUtils(self.db, self.logger).get_all_properties_names()
            ).set_max_items_in_a_row(2).inline()
        )
        await message.delete()

    ################## BASE CURRENCY SETTINGS HANDLERS ##################

    async def handler_choose_base_currency(self, callback: types.CallbackQuery, state: FSMContext):
        await self.send_silent_reply(
            callback,
            state,
            SETTINGS_BASE_CURRENCY_CHOICE,
            KBBuilder().set_buttons(
                self.supported_base_currencies
            ).not_title().inline()
        )
        await callback.message.delete()

    async def handler_set_base_currency(self, callback: types.CallbackQuery):
        up_utils = UsersPropertiesDbUtils(self.db, self.logger)
        await up_utils.set_property_value(
            callback.from_user.id,
            UserProperty.BASE_CURRENCY.value,
            {UserProperty.BASE_CURRENCY.value: callback.data},
            is_update=True
        )
        await callback.answer(SUCCESS_SETTINGS_SET, disable_notification=True)
        await callback.message.delete()

    ################## ACTIVE CATEGORIES SETTINGS HANDLERS ##################

    async def handler_set_categories(self, callback: types.CallbackQuery, state: FSMContext):
        chosen_categories = await UsersPropertiesDbUtils(self.db, self.logger) \
            .get_user_property(callback.from_user.id, UserProperty.CATEGORIES)
        categories = await CategoriesDbUtils(self.db, self.logger).get_all_categories()
        categories_map = {category: category in chosen_categories for category in categories}
        await state.update_data({UILabels.SETTINGS_CATEGORIES.value: categories_map})
        msg = await callback.message.reply(
            SETTINGS_CATEGORIES_VISIBILITY,
            reply_markup=KBBuilder().set_buttons(categories_map).switchers(),
            disable_notification=True
        )
        await callback.message.delete()
        await self.save_init_instruction_msg_id(msg, state)
        await state.set_state(self.state.settings_choosing_active_categories)

    async def handler_choosing_active_categories(self, callback: types.CallbackQuery, state: FSMContext, bot: Bot):
        cur_state_data = await state.get_data()
        categories_map = cur_state_data[UILabels.SETTINGS_CATEGORIES.value]

        if not callback.data == UILabels.CONFIRM.value:
            categories_map[callback.data] = not categories_map[callback.data]
            await state.update_data({UILabels.SETTINGS_CATEGORIES.value: categories_map})
            await callback.message.edit_reply_markup(
                reply_markup=KBBuilder().set_buttons(categories_map).switchers(),
                disable_notification=True
            )
            return
        
        await UsersPropertiesDbUtils(self.db, self.logger).set_property_value(
            callback.from_user.id,
            UserProperty.CATEGORIES.value,
            [cat for cat, is_active in categories_map.items() if is_active],
            is_update=True
        )
        await callback.answer(SUCCESS_SETTINGS_SET, disable_notification=True)
        await self.delete_init_instruction(callback.from_user.id, state, bot)
        await state.clear()

    ################## AMOUNTS AND COMMENTS SETTINGS HANDLERS ##################

    async def handler_choose_category(self, callback: types.CallbackQuery, state: FSMContext):
        await state.update_data({UILabels.SETTINGS_PROPERTY.value: UserProperty(callback.data)})
        up_utils = UsersPropertiesDbUtils(self.db, self.logger)
        categories = await up_utils.get_user_property(
            callback.from_user.id,
            UserProperty.CATEGORIES
        )
        
        await self.send_silent_reply(
            callback,
            state,
            SETTINGS_CATEGORIES_CHOICE,
            KBBuilder().set_buttons(categories).include_default().inline()
        )
        await callback.message.delete()
        await state.set_state(self.state.settings_request_values_for_category)

    async def handler_request_values_for_category(self, callback: types.CallbackQuery, state: FSMContext):
        state_data = await state.get_data()
        up_utils = UsersPropertiesDbUtils(self.db, self.logger)
        current_value = await up_utils.get_user_property(
            callback.from_user.id,
            state_data[UILabels.SETTINGS_PROPERTY.value],
            str((await CategoriesDbUtils(self.db, self.logger).get_category_by_name(callback.data)).category_id)
        )
        current_value = [escape_markdown(str(x), 2) for x in current_value]
        await state.update_data({UILabels.SETTINGS_PROPERTY_CATEGORY.value: callback.data})

        await self.send_silent_reply(
            callback,
            state,
            f"Current values: `{', '.join(current_value)}`\n\n" +
                SETTINGS_REQUEST_VALUES_FOR_CATEGORY,
            is_msg_text_markdown=True
        )
        await state.set_state(self.state.settings_parse_values_for_category)
        await callback.message.delete()

    async def handler_parse_values_for_category(self, message: types.Message, state: FSMContext, bot: Bot):
        state_data = await state.get_data()
        new_values = [v.strip() for v in message.text.split(",")]

        match state_data[UILabels.SETTINGS_PROPERTY.value]:
            case "amounts":
                try:
                    new_setting_val = [self.parse_expense_amount_input(v, True) for v in new_values]
                except ValueError:
                    await message.delete()
                    await self.send_silent_reply(message, state, ERROR_EXPENSE_AMOUNT_FORMAT)
                    return
            case _:
                new_setting_val = new_values

        await self.delete_init_instruction(message.chat.id, state, bot)
        up_utils = UsersPropertiesDbUtils(self.db, self.logger)
        await up_utils.set_property_value(
            message.from_user.id,
            state_data[UILabels.SETTINGS_PROPERTY.value].value,
            new_setting_val,
            category=state_data[UILabels.SETTINGS_PROPERTY_CATEGORY.value],
            is_update=True
        )

        msg = await message.answer(SUCCESS_SETTINGS_SET, disable_notification=True)
        await message.delete()
        await asyncio.sleep(5)
        await msg.delete()
        await state.clear()

    ################## BI SETTINGS HANDLERS ##################

    async def handler_setup_analytics(self, message: types.Message):
        superset = SupersetInterface()
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
        superset = SupersetInterface()
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

    ################## SHORTCUT SETTINGS HANDLERS ##################

    async def handler_manage_shortcuts(self, callback: types.CallbackQuery):
        await callback.answer()
        await callback.message.edit_reply_markup(
            str(callback.message.message_id),
            KBBuilder().set_buttons(
                [UILabels.SETTINGS_SHORTCUTS_ADD_EDIT.value,
                 UILabels.SETTINGS_SHORTCUTS_DELETE.value]
            ).inline()
        )

    async def handler_ask_shortcut_category(self, callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        await self.send_silent_reply(
            callback,
            state,
            ASK_EXPENSE_CATEGORY,
            KBBuilder().set_buttons(
                await CategoriesDbUtils(self.db, self.logger).get_all_categories()
            ).inline()
        )
        await state.set_state(self.state.settings_ask_shortcut_amount)
        await callback.message.delete()

    async def handler_parse_shortcut_category(self, callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        await state.update_data({
            ShortcutLabels.SHORTCUT_PAYLOADS.value: {
                ShortcutLabels.SHORTCUT_PAYLOAD_CATEGORY.value: callback.data
            }
        })
        await self.send_silent_reply(callback, state, ASK_EXPENSE_AMOUNT)
        await state.set_state(self.state.settings_parse_shortcut_amount)
        await callback.message.delete()

    async def handler_parse_shortcut_amount(self, message: types.Message, state: FSMContext, bot: Bot):
        cur_state_data = await state.get_data()

        try:
            shortcut_amount_val = self.parse_expense_amount_input(message.text, True)
        except ValueError:
            await self.send_silent_reply(message, state, ERROR_EXPENSE_AMOUNT_FORMAT)
            return

        await self.delete_init_instruction(message.chat.id, state, bot)
        await state.update_data({
            ShortcutLabels.SHORTCUT_PAYLOADS.value: {
                **cur_state_data[ShortcutLabels.SHORTCUT_PAYLOADS.value],
                ShortcutLabels.SHORTCUT_PAYLOAD_AMOUNT.value: shortcut_amount_val
            }
        })
        await self.send_silent_reply(message, state, SETTINGS_ASK_SHORTCUT_NAME)
        await state.set_state(self.state.settings_ask_shortcut_name)
        await message.delete()

    async def handler_add_shortcut(self, message: types.Message, state: FSMContext, bot: Bot):
        is_first_shortcut = False
        cur_state_data = await state.get_data()
        up_utils = UsersPropertiesDbUtils(self.db, self.logger)

        await self.delete_init_instruction(message.chat.id, state, bot)
        cur_prop_value = await up_utils.get_user_property(
            message.from_user.id,
            UserProperty.SHORTCUTS
        )
        if not cur_prop_value:
            cur_prop_value = {}
            is_first_shortcut = True
        cur_prop_value[message.text] = cur_state_data[ShortcutLabels.SHORTCUT_PAYLOADS.value]
        await up_utils.set_property_value(
            message.from_user.id,
            UserProperty.SHORTCUTS.value,
            cur_prop_value,
            is_update=not is_first_shortcut
        )

        msg = await message.answer(SUCCESS_SETTINGS_SET, disable_notification=True)
        await message.delete()
        await asyncio.sleep(5)
        await msg.delete()

    async def handler_ask_shortcut_to_delete(self, callback: types.CallbackQuery, state: FSMContext):
        up_utils = UsersPropertiesDbUtils(self.db, self.logger)
        cur_shortcuts = await up_utils.get_user_property(
            callback.from_user.id,
            UserProperty.SHORTCUTS
        )

        if not cur_shortcuts:
            await callback.answer("⚠️No shortcuts to delete.")
            await callback.message.delete()
            return

        await callback.message.reply(
            "Which shortcut to delete?",
            reply_markup=KBBuilder().set_buttons(cur_shortcuts.keys()).inline()
        )
        await state.set_state(self.state.settings_delete_shortcut)
        await callback.message.delete()

    async def handler_delete_shortcut(self, callback: types.CallbackQuery, state: FSMContext):
        up_utils = UsersPropertiesDbUtils(self.db, self.logger)
        cur_shortcuts = await up_utils.get_user_property(
            callback.from_user.id,
            UserProperty.SHORTCUTS
        )
        cur_shortcuts.pop(callback.data)
        await up_utils.set_property_value(
            callback.from_user.id,
            UserProperty.SHORTCUTS.value,
            cur_shortcuts,
            is_update=True
        )

        await callback.answer(f"✅ Shortcut '{callback.data}' deleted")
        await callback.message.delete()
        await state.clear()
