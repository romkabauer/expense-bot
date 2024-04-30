from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from resources.helpers import chunk_list


def build_date_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="today", callback_data="today"),
            InlineKeyboardButton(text="yesterday", callback_data="yesterday"),
            InlineKeyboardButton(text="earlier", callback_data="other_date")
        ]
    ])


def build_reply_keyboard(entities: list[str],
                         max_items_in_a_row: int = 2,
                         additional_items=None):
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=str(item)) for item in chunk]
        for chunk in chunk_list(entities if not additional_items else entities + additional_items,
                                max_items_in_a_row)
    ])

def build_switchers_keyboard(entities: dict[str, bool],
                             max_items_in_a_row: int = 2,
                             stopper_name: str = "Confirm!"):
    buttons = [
            [InlineKeyboardButton(text="✅" + str(item) if entities[item] else "🔲" + str(item),
                                  callback_data=str(item)) for item in chunk]
            for chunk in chunk_list(entities.keys(), max_items_in_a_row)
        ]
    buttons.append([InlineKeyboardButton(text=stopper_name,
                                         callback_data=stopper_name)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def build_listlike_keyboard(entities: list[str],
                            additional_items: list[str] | None = None,
                            max_items_in_a_row: int = 2,
                            title_button_names: bool = True):
    buttons = [
            [InlineKeyboardButton(text=str(item).replace("_", " ").title()
                                       if title_button_names
                                       else str(item).replace("_", " "),
                                  callback_data=str(item)) for item in chunk]
            for chunk in chunk_list(entities if not additional_items else entities+additional_items,
                                    max_items_in_a_row)
        ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
