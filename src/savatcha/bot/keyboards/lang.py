from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class LangCB(CallbackData, prefix="lang"):
    code: str


def lang_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🇺🇿 O'zbekcha", callback_data=LangCB(code="uz"))
    kb.button(text="🇷🇺 Русский", callback_data=LangCB(code="ru"))
    kb.adjust(2)
    return kb.as_markup()
