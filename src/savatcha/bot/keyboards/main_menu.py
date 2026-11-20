from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from savatcha.bot.keyboards.common import labels
from savatcha.core.i18n import t

MENU_KEYS = ("menu_catalog", "menu_cart", "menu_orders", "menu_lang", "menu_contact")


menu_labels = labels


def main_menu(lang: str | None) -> ReplyKeyboardMarkup:
    b = {k: KeyboardButton(text=t(k, lang)) for k in MENU_KEYS}
    return ReplyKeyboardMarkup(
        keyboard=[
            [b["menu_catalog"], b["menu_cart"]],
            [b["menu_orders"], b["menu_lang"]],
            [b["menu_contact"]],
        ],
        resize_keyboard=True,
    )
