from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from savatcha.bot.keyboards.common import noop_button
from savatcha.core.i18n import t
from savatcha.core.services.cart import Cart
from savatcha.core.services.catalog import localized


class CartCB(CallbackData, prefix="cart"):
    act: str  # inc | dec | del | clear | checkout
    id: int = 0


class ConfirmCB(CallbackData, prefix="cf"):
    ok: bool


def cart_kb(cart: Cart, lang: str | None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for line in cart.lines:
        pid = line.product.id
        name = localized(line.product, "name", lang)
        rows.append(
            [
                InlineKeyboardButton(text="➖", callback_data=CartCB(act="dec", id=pid).pack()),
                noop_button(f"{name[:18]} · {line.quantity}"),
                InlineKeyboardButton(text="➕", callback_data=CartCB(act="inc", id=pid).pack()),
                InlineKeyboardButton(text="❌", callback_data=CartCB(act="del", id=pid).pack()),
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=t("btn_checkout", lang), callback_data=CartCB(act="checkout").pack()
            ),
            InlineKeyboardButton(
                text=t("btn_clear_cart", lang), callback_data=CartCB(act="clear").pack()
            ),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_kb(lang: str | None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("btn_confirm", lang), callback_data=ConfirmCB(ok=True).pack()
                ),
                InlineKeyboardButton(
                    text=t("btn_cancel", lang), callback_data=ConfirmCB(ok=False).pack()
                ),
            ]
        ]
    )
