from aiogram.dispatcher.filters.state import State, StatesGroup


class States(StatesGroup):
    picking_day = State()
    entering_amount = State()
    commenting = State()
    shortcut = State()
    picking_day_shortcut = State()
    shortcut_parsing = State()
