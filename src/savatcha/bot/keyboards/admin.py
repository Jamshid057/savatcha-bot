from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from savatcha.bot.keyboards.common import noop_button
from savatcha.bot.utils import total_pages
from savatcha.core.db.models import Category, Order, Product
from savatcha.core.i18n import t
from savatcha.core.services.formatting import status_label
from savatcha.core.services.orders import ORDERS_PAGE_SIZE, STATUS_GROUPS, TRANSITIONS
from savatcha.core.utils.money import format_price


class AdminCB(CallbackData, prefix="adm"):
    act: str  # menu | products | categories | orders | stats


class AdmCatCB(CallbackData, prefix="ac"):
    act: str  # list | open | add | rename | toggle | del | del_ok
    id: int = 0


class AdmProdCB(CallbackData, prefix="ap"):
    act: str  # cats | list | open | add | edit | avail | arch | arch_ok
    id: int = 0
    f: str = ""
    cat: int = 0
    page: int = 1


class AdmOrderCB(CallbackData, prefix="ao"):
    act: str  # list | open | st | rc
    id: int = 0
    s: str = ""
    g: str = "new"
    page: int = 1


def _btn(text: str, cb: CallbackData) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=cb.pack())


def back_to_admin(lang: str | None) -> list[InlineKeyboardButton]:
    return [_btn(t("btn_back", lang), AdminCB(act="menu"))]


def admin_menu_kb(lang: str | None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn(t("adm_products", lang), AdminCB(act="products"))],
            [_btn(t("adm_categories", lang), AdminCB(act="categories"))],
            [_btn(t("adm_orders", lang), AdminCB(act="orders"))],
            [_btn(t("adm_stats", lang), AdminCB(act="stats"))],
        ]
    )


def new_order_kb(order_id: int, lang: str | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _btn(t("btn_accept", lang), AdmOrderCB(act="st", id=order_id, s="accepted")),
                _btn(t("btn_reject", lang), AdmOrderCB(act="st", id=order_id, s="cancelled")),
            ],
            [_btn(t("btn_details", lang), AdmOrderCB(act="open", id=order_id))],
        ]
    )


# ---- kategoriyalar ----
def categories_admin_kb(cats: list[Category], lang: str | None) -> InlineKeyboardMarkup:
    rows = [
        [
            _btn(
                f"{'✅' if c.is_active else '🚫'} {c.name_uz} / {c.name_ru}",
                AdmCatCB(act="open", id=c.id),
            )
        ]
        for c in cats
    ]
    rows.append([_btn(t("btn_add", lang), AdmCatCB(act="add"))])
    rows.append(back_to_admin(lang))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def category_kb(cat: Category, lang: str | None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn(t("btn_rename", lang), AdmCatCB(act="rename", id=cat.id))],
            [
                _btn(
                    t("btn_deactivate" if cat.is_active else "btn_activate", lang),
                    AdmCatCB(act="toggle", id=cat.id),
                )
            ],
            [_btn(t("btn_delete", lang), AdmCatCB(act="del", id=cat.id))],
            [_btn(t("btn_back", lang), AdmCatCB(act="list"))],
        ]
    )


def category_delete_confirm_kb(cat_id: int, lang: str | None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _btn(t("btn_confirm", lang), AdmCatCB(act="del_ok", id=cat_id)),
                _btn(t("btn_cancel", lang), AdmCatCB(act="open", id=cat_id)),
            ]
        ]
    )


# ---- mahsulotlar ----
def product_cats_kb(cats: list[Category], lang: str | None) -> InlineKeyboardMarkup:
    rows = [[_btn(c.name_uz, AdmProdCB(act="list", cat=c.id))] for c in cats]
    rows.append([_btn(t("btn_add", lang), AdmProdCB(act="add"))])
    rows.append(back_to_admin(lang))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def choose_cat_for_add_kb(cats: list[Category], lang: str | None) -> InlineKeyboardMarkup:
    rows = [[_btn(c.name_uz, AdmProdCB(act="add", cat=c.id))] for c in cats]
    rows.append([_btn(t("btn_back", lang), AdmProdCB(act="cats"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_list_kb(
    products: list[Product], total: int, cat_id: int, page: int, lang: str | None
) -> InlineKeyboardMarkup:
    rows = []
    for p in products:
        mark = "✅" if p.is_available else "🚫"
        rows.append(
            [
                _btn(
                    f"{mark} {p.name_uz} — {format_price(p.price)}"[:60],
                    AdmProdCB(act="open", id=p.id, cat=cat_id, page=page),
                )
            ]
        )
    pages = total_pages(total)
    if pages > 1:
        rows.append(
            [
                _btn("◀️", AdmProdCB(act="list", cat=cat_id, page=max(1, page - 1))),
                noop_button(f"{page}/{pages}"),
                _btn("▶️", AdmProdCB(act="list", cat=cat_id, page=min(pages, page + 1))),
            ]
        )
    rows.append([_btn(t("btn_add", lang), AdmProdCB(act="add", cat=cat_id))])
    rows.append([_btn(t("btn_back", lang), AdmProdCB(act="cats"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_admin_kb(product: Product, lang: str | None) -> InlineKeyboardMarkup:
    def edit(field: str, key: str) -> InlineKeyboardButton:
        return _btn(t(key, lang), AdmProdCB(act="edit", id=product.id, f=field))

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [edit("name_uz", "fld_name_uz"), edit("name_ru", "fld_name_ru")],
            [edit("description_uz", "fld_desc_uz"), edit("description_ru", "fld_desc_ru")],
            [edit("price", "fld_price"), edit("image", "fld_image")],
            [
                _btn(t("btn_toggle_avail", lang), AdmProdCB(act="avail", id=product.id)),
                _btn(t("btn_archive", lang), AdmProdCB(act="arch", id=product.id)),
            ],
            [_btn(t("btn_back", lang), AdmProdCB(act="list", cat=product.category_id))],
        ]
    )


def archive_confirm_kb(product_id: int, lang: str | None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _btn(t("btn_confirm", lang), AdmProdCB(act="arch_ok", id=product_id)),
                _btn(t("btn_cancel", lang), AdmProdCB(act="open", id=product_id)),
            ]
        ]
    )


# ---- buyurtmalar ----
def orders_list_kb(
    orders: list[Order], total: int, group: str, page: int, lang: str | None
) -> InlineKeyboardMarkup:
    rows = [
        [
            _btn(
                f"#{o.id} · {o.customer_name[:18]} · {format_price(o.total)}",
                AdmOrderCB(act="open", id=o.id, g=group, page=page),
            )
        ]
        for o in orders
    ]
    pages = total_pages(total, ORDERS_PAGE_SIZE)
    if pages > 1:
        rows.append(
            [
                _btn("◀️", AdmOrderCB(act="list", g=group, page=max(1, page - 1))),
                noop_button(f"{page}/{pages}"),
                _btn("▶️", AdmOrderCB(act="list", g=group, page=min(pages, page + 1))),
            ]
        )
    rows.insert(0, orders_filter_row(group, lang))
    rows.append(back_to_admin(lang))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def orders_filter_row(group: str, lang: str | None) -> list[InlineKeyboardButton]:
    return [
        _btn(("• " if g == group else "") + t(f"grp_{g}", lang), AdmOrderCB(act="list", g=g))
        for g in STATUS_GROUPS
    ]


def order_admin_kb(order: Order, group: str, page: int, lang: str | None) -> InlineKeyboardMarkup:
    rows = [
        [
            _btn(
                "→ " + status_label(s, lang),
                AdmOrderCB(act="st", id=order.id, s=s, g=group, page=page),
            )
        ]
        for s in TRANSITIONS[order.status]
    ]
    if order.receipt_path:
        rows.append([_btn(t("btn_receipt", lang), AdmOrderCB(act="rc", id=order.id))])
    rows.append([_btn(t("btn_back", lang), AdmOrderCB(act="list", g=group, page=page))])
    return InlineKeyboardMarkup(inline_keyboard=rows)
