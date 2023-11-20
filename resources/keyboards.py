from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from resources.helpers import chunk_list


def build_date_keyboard():
    return InlineKeyboardMarkup(3, [
        [
            InlineKeyboardButton(text="today", callback_data="today"),
            InlineKeyboardButton(text="yesterday", callback_data="yesterday"),
            InlineKeyboardButton(text="earlier", callback_data="other_date")
        ]
    ])


def build_reply_keyboard(entities: list[str],
                         max_items_in_a_row: int = 2,
                         additional_items=None):
    return ReplyKeyboardMarkup([
        [KeyboardButton(text=str(item)) for item in chunk]
        for chunk in chunk_list(entities if not additional_items else entities + additional_items,
                                max_items_in_a_row)
    ])


def build_listlike_keyboard(entities: list[str],
                            max_items_in_a_row: int = 2,
                            additional_items=None):
    buttons = [
            [InlineKeyboardButton(text=str(item), callback_data=str(item)) for item in chunk]
            for chunk in chunk_list(entities if not additional_items else entities+additional_items,
                                    max_items_in_a_row)
    ]
    return InlineKeyboardMarkup(3, buttons)
