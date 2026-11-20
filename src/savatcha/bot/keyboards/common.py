from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup

from savatcha.core.i18n import SUPPORTED, t


class MenuCB(CallbackData, prefix="m"):
    act: str  # cats | search | orders | noop


def noop_button(text: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=MenuCB(act="noop").pack())


def labels(key: str) -> set[str]:
    """Reply tugma matni ikkala tilda ham (handler filtri uchun)."""
    return {t(key, lang) for lang in SUPPORTED}


def reply_kb(rows: list[list[KeyboardButton]]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def cancel_button(lang: str | None) -> KeyboardButton:
    return KeyboardButton(text=t("btn_cancel", lang))
