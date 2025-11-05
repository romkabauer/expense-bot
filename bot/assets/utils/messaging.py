import re
from itertools import islice

from pydantic import validate_call
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)

from static.literals import UILabels


def chunk_list(list_to_split: list, chunk_size: int):
    list_to_split = iter(list_to_split)
    res = iter(lambda: list(islice(list_to_split, chunk_size)), list())
    return list(res)

def escape_markdown(text: str, version: int = 1, entity_type: str = None) -> str:
    """
    Helper function to escape telegram markup symbols.

    Args:
        text (:obj:`str`): The text.
        version (:obj:`int` | :obj:`str`): Use to specify the version of telegrams Markdown.
            Either ``1`` or ``2``. Defaults to ``1``.
        entity_type (:obj:`str`, optional): For the entity types ``PRE``, ``CODE`` and the link
            part of ``TEXT_LINKS``, only certain characters need to be escaped in ``MarkdownV2``.
            See the official API documentation for details. Only valid in combination with
            ``version=2``, will be ignored else.
    """
    if int(version) == 1:
        escape_chars = r'_*`['
    elif int(version) == 2:
        if entity_type in ['pre', 'code']:
            escape_chars = r'\`'
        elif entity_type == 'text_link':
            escape_chars = r'\)'
        else:
            escape_chars = r'_*[]()~`>#+-=|{}.!'
    else:
        raise ValueError('Markdown version must be either 1 or 2!')

    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)


class KBBuilder:
    def __init__(self):
        """
        Args:
            buttons (list[str] | dict[str, str|bool|int|float]):
            used for labels and data assignment.
            If `dict[str, str|bool|int|float]` provided, keys are labels, values are data.
        """
        self.buttons: list[str] | dict[str, str|bool|int|float]  = [UILabels.DEFAULT.value]
        self.max_items_in_a_row: int = 3
        self.include_back_button: bool = False
        self.include_default_button: bool = False
        self.title_button_labels: bool = True

    @property
    def buttons(self) -> list[str] | dict[str, str|bool|int|float]:
        return self._buttons

    @buttons.setter
    @validate_call
    def buttons(self, v: list[str] | dict[str, str|bool|int|float]):
        if not v:
            raise ValueError("buttons must not be empty!")
        self._buttons = v

    @property
    def max_items_in_a_row(self) -> int:
        return self._max_items_in_a_row

    @max_items_in_a_row.setter
    @validate_call
    def max_items_in_a_row(self, v: int):
        if not v:
            raise ValueError("max_items_in_a_row must not be None!")
        if v and v < 0:
            raise ValueError("max_items_in_a_row must be a positive integer!")
        self._max_items_in_a_row = v

    def set_buttons(self, v: list[str] | dict[str, str|bool|int|float]):
        self.buttons = v
        return self

    def set_max_items_in_a_row(self, v: int):
        self.max_items_in_a_row = v
        return self

    def include_back(self):
        self.include_back_button = True
        return self

    def include_default(self):
        self.include_default_button = True
        return self

    def not_title(self):
        self.title_button_labels = False
        return self

    def inline(self) -> InlineKeyboardMarkup:
        """
        Takes button map and builds InlineKeyboardMarkup.
        Labels will have '_' replaced with space.

        Returns:
            InlineKeyboardMarkup
        """
        if not self.buttons:
            raise ValueError

        kyb = InlineKeyboardMarkup(inline_keyboard=[])
        if isinstance(self.buttons, list):
            kyb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=str(item).replace("_", " ").title()
                                if self.title_button_labels
                                else str(item).replace("_", " "),
                            callback_data=str(item)
                        ) for item in chunk
                    ]
                    for chunk in chunk_list(self.buttons, self.max_items_in_a_row)
                ]
            )
        if isinstance(self.buttons, dict):
            kyb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=str(k).replace("_", " ").title()
                                if self.title_button_labels
                                else str(k).replace("_", " "),
                            callback_data=str(v)
                        )
                        for k, v in chunk
                    ]
                    for chunk in chunk_list(list(self.buttons.items()), self.max_items_in_a_row)
                ]
            )
        if self.include_back_button:
            kyb.inline_keyboard.append([
                InlineKeyboardButton(
                    text=UILabels.BACK.value.title(),
                    callback_data=UILabels.BACK.value
                )
            ])
        if self.include_default_button:
            kyb.inline_keyboard.append([
                InlineKeyboardButton(
                    text=UILabels.DEFAULT.value.title(),
                    callback_data=UILabels.DEFAULT.value
                )
            ])
        return kyb

    def reply(self) -> ReplyKeyboardMarkup:
        kyb = ReplyKeyboardMarkup(keyboard=[
            [
                KeyboardButton(text=str(item))
                for item in chunk
            ]
            for chunk in chunk_list(self.buttons, self.max_items_in_a_row)
        ])
        if self.include_back_button:
            kyb.keyboard.append([
                KeyboardButton(text=UILabels.BACK.value.title())
            ])
        if self.include_default_button:
            kyb.keyboard.append([
                KeyboardButton(text=UILabels.DEFAULT.value.title())
            ])

        return kyb

    @validate_call
    def switchers(self, stopper: str = UILabels.CONFIRM.value):
        if not isinstance(self.buttons, dict) \
           and not isinstance(self.buttons.items()[0][1], bool):
            ValueError("Incompatible buttons map, should be dict[str, bool]!")

        buttons = [
            [
                InlineKeyboardButton(
                    text="✅" + str(item) if self.buttons[item] else "🔲" + str(item),
                    callback_data=str(item)
                )
                for item in chunk
            ]
            for chunk in chunk_list(self.buttons.keys(), self.max_items_in_a_row)
        ]
        buttons.append([InlineKeyboardButton(text=stopper, callback_data=stopper)])

        return InlineKeyboardMarkup(inline_keyboard=buttons)

    def build_date_kb(self):
        self.buttons = {
            UILabels.TODAY.value: UILabels.TODAY.value,
            UILabels.YESTERDAY.value: UILabels.YESTERDAY.value,
            "earlier": UILabels.ANOTHER_DATE.value
        }
        self.title_button_labels = False
        return self.inline()

    def build_edit_mode_main_kb(self):
        self.buttons = [UILabels.EDIT.value, UILabels.DELETE.value]
        self.title_button_labels = True
        return self.inline()
