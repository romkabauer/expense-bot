from aiogram.fsm.state import State, StatesGroup


class States(StatesGroup):
    other_date_input = State()
    reading_expense_category = State()
    entering_amount = State()
    commenting = State()
    shortcut = State()
    shortcut_parsing = State()
    ask_values_for_category = State()
    setting_values_for_category = State()
