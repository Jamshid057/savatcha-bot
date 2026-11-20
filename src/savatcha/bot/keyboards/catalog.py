from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from savatcha.bot.keyboards.common import MenuCB, noop_button
from savatcha.bot.utils import total_pages
from savatcha.core.db.models import Category, Product
from savatcha.core.i18n import t
from savatcha.core.services.cart import MAX_QTY
from savatcha.core.services.catalog import localized
from savatcha.core.utils.money import format_price


class CatCB(CallbackData, prefix="cat"):
    id: int
    page: int = 1


class SearchPageCB(CallbackData, prefix="sp"):
    page: int


class ProdCB(CallbackData, prefix="pr"):
    id: int


class QtyCB(CallbackData, prefix="qty"):
    id: int
    q: int


class AddCB(CallbackData, prefix="add"):
    id: int
    q: int


def categories_kb(categories: list[Category], lang: str | None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for cat in categories:
        kb.button(text=localized(cat, "name", lang), callback_data=CatCB(id=cat.id))
    kb.adjust(2)
    kb.row(
        InlineKeyboardButton(text=t("btn_search", lang), callback_data=MenuCB(act="search").pack())
    )
    return kb.as_markup()


def products_kb(
    products: list[Product],
    total: int,
    page: int,
    lang: str | None,
    *,
    category_id: int | None = None,
) -> InlineKeyboardMarkup:
    """`category_id=None` — qidiruv natijalari."""
    rows: list[list[InlineKeyboardButton]] = []
    for p in products:
        mark = "" if p.is_available else "🚫 "
        label = f"{mark}{localized(p, 'name', lang)} — {format_price(p.price, lang)}"
        rows.append([InlineKeyboardButton(text=label[:60], callback_data=ProdCB(id=p.id).pack())])
    pages = total_pages(total)
    if pages > 1:

        def go(p: int) -> str:
            if category_id is None:
                return SearchPageCB(page=p).pack()
            return CatCB(id=category_id, page=p).pack()

        rows.append(
            [
                InlineKeyboardButton(text="◀️", callback_data=go(max(1, page - 1))),
                noop_button(f"{page}/{pages}"),
                InlineKeyboardButton(text="▶️", callback_data=go(min(pages, page + 1))),
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=t("btn_back_cats", lang), callback_data=MenuCB(act="cats").pack()
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_card_kb(product_id: int, qty: int, lang: str | None) -> InlineKeyboardMarkup:
    qty = max(1, min(MAX_QTY, qty))
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➖", callback_data=QtyCB(id=product_id, q=max(1, qty - 1)).pack()
                ),
                noop_button(str(qty)),
                InlineKeyboardButton(
                    text="➕", callback_data=QtyCB(id=product_id, q=min(MAX_QTY, qty + 1)).pack()
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("btn_add_to_cart", lang),
                    callback_data=AddCB(id=product_id, q=qty).pack(),
                )
            ],
        ]
    )
