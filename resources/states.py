from aiogram.fsm.state import State, StatesGroup


class States(StatesGroup):
    other_date_input = State()
    entering_amount = State()
    commenting = State()
    shortcut = State()
