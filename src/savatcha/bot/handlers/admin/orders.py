import logging

from aiogram import Bot, F
from aiogram.types import CallbackQuery, FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.bot.filters import admin_router
from savatcha.bot.keyboards.admin import (
    AdminCB,
    AdmOrderCB,
    order_admin_kb,
    orders_list_kb,
)
from savatcha.bot.utils import safe_edit
from savatcha.core.config import get_settings
from savatcha.core.db.models import User
from savatcha.core.i18n import t
from savatcha.core.services import orders as order_service
from savatcha.core.services.files import resolve_path
from savatcha.core.services.formatting import format_order_text
from savatcha.core.services.notify import notify_user_status_changed
from savatcha.core.utils.text import split_text

log = logging.getLogger(__name__)
router = admin_router("admin_orders")


async def _show_list(
    call: CallbackQuery, session: AsyncSession, group: str, page: int, lang: str | None
) -> None:
    orders, total = await order_service.list_orders(session, group=group, page=page)
    title = t("adm_orders_title", lang, total=total) if orders else t("adm_orders_none", lang)
    await safe_edit(call.message, title, orders_list_kb(orders, total, group, page, lang))


@router.callback_query(AdminCB.filter(F.act == "orders"))
async def open_orders(call: CallbackQuery, session: AsyncSession, lang: str | None) -> None:
    await call.answer()
    await _show_list(call, session, "new", 1, lang)


@router.callback_query(AdmOrderCB.filter(F.act == "list"))
async def list_orders(
    call: CallbackQuery, callback_data: AdmOrderCB, session: AsyncSession, lang: str | None
) -> None:
    await call.answer()
    group = callback_data.g if callback_data.g in order_service.STATUS_GROUPS else "new"
    await _show_list(call, session, group, callback_data.page, lang)


async def _show_order(
    call: CallbackQuery,
    session: AsyncSession,
    order_id: int,
    group: str,
    page: int,
    lang: str | None,
) -> None:
    order = await order_service.get_order(session, order_id)
    if order is None:
        await safe_edit(call.message, t("order_not_found", lang))
        return
    parts = split_text(format_order_text(order, lang, admin=True))
    history = "\n".join(
        f"{h.created_at.strftime('%d.%m %H:%M')} · "
        f"{t(f'status_{h.from_status}', lang) + ' → ' if h.from_status else ''}"
        f"{t(f'status_{h.to_status}', lang)}"
        for h in order.history
    )
    text = parts[0] if len(parts) > 1 else f"{parts[0]}\n\n{t('order_history', lang)}\n{history}"
    await safe_edit(call.message, text[:4000], order_admin_kb(order, group, page, lang))


@router.callback_query(AdmOrderCB.filter(F.act == "open"))
async def open_order(
    call: CallbackQuery, callback_data: AdmOrderCB, session: AsyncSession, lang: str | None
) -> None:
    await call.answer()
    await _show_order(call, session, callback_data.id, callback_data.g, callback_data.page, lang)


@router.callback_query(AdmOrderCB.filter(F.act == "st"))
async def change_status(
    call: CallbackQuery,
    callback_data: AdmOrderCB,
    session: AsyncSession,
    lang: str | None,
    bots: dict[str, Bot],
) -> None:
    order = await order_service.get_order(session, callback_data.id)
    if order is None:
        await call.answer(t("order_not_found", lang), show_alert=True)
        return
    try:
        await order_service.change_status(session, order, callback_data.s, call.from_user.id)
    except order_service.InvalidTransition:
        await call.answer(t("status_not_allowed", lang), show_alert=True)
        await _show_order(call, session, order.id, callback_data.g, callback_data.page, lang)
        return
    await call.answer(t("status_changed", lang))
    await _show_order(call, session, order.id, callback_data.g, callback_data.page, lang)
    customer = await session.get(User, order.user_id)
    if customer is not None:
        await notify_user_status_changed(bots, order, customer.tg_id, customer.lang)


@router.callback_query(AdmOrderCB.filter(F.act == "rc"))
async def send_receipt(
    call: CallbackQuery, callback_data: AdmOrderCB, session: AsyncSession, lang: str | None
) -> None:
    order = await order_service.get_order(session, callback_data.id)
    path = (
        resolve_path(get_settings().upload_dir, order.receipt_path)
        if order and order.receipt_path
        else None
    )
    if path is None:
        await call.answer(t("receipt_missing", lang), show_alert=True)
        return
    await call.answer()
    if isinstance(call.message, Message):
        await call.message.answer_photo(
            FSInputFile(path),
            caption=t("receipt_caption", lang, id=order.id),  # type: ignore[union-attr]
        )
