from aiogram.fsm.state import State, StatesGroup


class States(StatesGroup):
    other_date_input = State()
    reading_expense_category = State()
    entering_amount = State()
    commenting = State()
    shortcut = State()
    shortcut_parsing = State()

    settings_request_values_for_category = State()
    settings_parse_values_for_category = State()
    settings_choosing_active_categories = State()
    settings_ask_shortcut_amount = State()
    settings_parse_shortcut_amount = State()
    settings_ask_shortcut_name = State()

    edit_mode = State()
    edit_date = State()
    edit_category = State()
    delete_mode = State()
