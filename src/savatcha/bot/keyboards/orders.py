from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from savatcha.bot.keyboards.common import MenuCB
from savatcha.core.db.models import Order
from savatcha.core.i18n import t
from savatcha.core.services.formatting import status_label
from savatcha.core.utils.money import format_price


class OrderViewCB(CallbackData, prefix="ov"):
    id: int


def my_orders_kb(orders: list[Order], lang: str | None) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"#{o.id} · {status_label(o.status, lang)} · {format_price(o.total, lang)}",
                callback_data=OrderViewCB(id=o.id).pack(),
            )
        ]
        for o in orders
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def order_back_kb(lang: str | None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("btn_back", lang), callback_data=MenuCB(act="orders").pack()
                )
            ]
        ]
    )
