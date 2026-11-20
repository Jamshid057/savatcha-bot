import logging

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.bot.handlers.cart import cart_text
from savatcha.bot.keyboards.admin import new_order_kb
from savatcha.bot.keyboards.cart import CartCB, ConfirmCB, confirm_kb
from savatcha.bot.keyboards.common import cancel_button, labels, reply_kb
from savatcha.bot.keyboards.main_menu import main_menu
from savatcha.bot.states import Checkout
from savatcha.bot.utils import download_photo
from savatcha.core.config import get_settings
from savatcha.core.db.models import User
from savatcha.core.i18n import t
from savatcha.core.repo import users
from savatcha.core.services import cart as cart_service
from savatcha.core.services import orders as order_service
from savatcha.core.services.files import RECEIPTS_SUBDIR, ImageError, save_image
from savatcha.core.services.notify import notify_admins_new_order
from savatcha.core.utils.phone import normalize_phone

log = logging.getLogger(__name__)
router = Router(name="checkout")


def _kb(lang: str | None, *top: KeyboardButton) -> ReplyKeyboardMarkup:
    rows = [[b] for b in top]
    rows.append([cancel_button(lang)])
    return reply_kb(rows)


@router.callback_query(CartCB.filter(F.act == "checkout"))
async def start_checkout(
    call: CallbackQuery, state: FSMContext, session: AsyncSession, user: User, lang: str | None
) -> None:
    cart = await cart_service.get_cart(session, user.id)
    if not cart.lines:
        await call.answer(t("cart_empty", lang), show_alert=True)
        return
    await call.answer()
    await state.clear()
    await state.set_state(Checkout.name)
    if isinstance(call.message, Message):
        await call.message.answer(
            t("ask_name", lang), reply_markup=_kb(lang, KeyboardButton(text=user.full_name))
        )


@router.message(StateFilter(Checkout), F.text.in_(labels("btn_cancel")))
async def cancel_checkout(message: Message, state: FSMContext, lang: str | None) -> None:
    await state.clear()
    await message.answer(t("order_cancelled", lang), reply_markup=main_menu(lang))


@router.message(Checkout.name, F.text)
async def got_name(message: Message, state: FSMContext, lang: str | None) -> None:
    name = (message.text or "").strip()
    if not 2 <= len(name) <= 100:
        await message.answer(t("name_invalid", lang))
        return
    await state.update_data(name=name)
    await state.set_state(Checkout.phone)
    await message.answer(
        t("ask_phone", lang),
        reply_markup=_kb(
            lang, KeyboardButton(text=t("btn_share_contact", lang), request_contact=True)
        ),
    )


@router.message(Checkout.phone, F.contact | F.text)
async def got_phone(message: Message, state: FSMContext, lang: str | None) -> None:
    if message.contact:
        if message.contact.user_id not in (None, message.from_user.id if message.from_user else 0):
            await message.answer(t("contact_not_own", lang))
            return
        raw = message.contact.phone_number
    else:
        raw = message.text or ""
    phone = normalize_phone(raw)
    if phone is None:
        await message.answer(t("phone_invalid", lang))
        return
    await state.update_data(phone=phone)
    await state.set_state(Checkout.address)
    await message.answer(t("ask_address", lang), reply_markup=_kb(lang))


@router.message(Checkout.address, F.text)
async def got_address(message: Message, state: FSMContext, lang: str | None) -> None:
    address = (message.text or "").strip()
    if not 5 <= len(address) <= 300:
        await message.answer(t("address_invalid", lang))
        return
    await state.update_data(address=address)
    await state.set_state(Checkout.comment)
    await message.answer(
        t("ask_comment", lang), reply_markup=_kb(lang, KeyboardButton(text=t("btn_skip", lang)))
    )


async def _ask_receipt(message: Message, state: FSMContext, lang: str | None) -> None:
    await state.set_state(Checkout.receipt)
    if get_settings().require_receipt:
        await message.answer(t("ask_receipt", lang), reply_markup=_kb(lang))
    else:
        await message.answer(
            t("ask_receipt_optional", lang),
            reply_markup=_kb(lang, KeyboardButton(text=t("btn_skip", lang))),
        )


@router.message(Checkout.comment, F.text)
async def got_comment(message: Message, state: FSMContext, lang: str | None) -> None:
    text = (message.text or "").strip()
    comment = "" if text in labels("btn_skip") else text[:500]
    await state.update_data(comment=comment)
    await _ask_receipt(message, state, lang)


async def _show_confirm(
    message: Message, state: FSMContext, session: AsyncSession, user: User, lang: str | None
) -> None:
    cart = await cart_service.get_cart(session, user.id)
    if not cart.lines:
        await state.clear()
        await message.answer(t("cart_empty", lang), reply_markup=main_menu(lang))
        return
    d = await state.get_data()
    parts = [
        t("confirm_title", lang),
        "",
        cart_text(cart, lang),
        "",
        t("order_customer", lang, name=d["name"], phone=d["phone"]),
        t("order_address", lang, address=d["address"]),
    ]
    if d.get("comment"):
        parts.append(t("order_comment", lang, comment=d["comment"]))
    if d.get("receipt"):
        parts.append(t("order_has_receipt", lang))
    await state.set_state(Checkout.confirm)
    await message.answer("\n".join(parts), reply_markup=confirm_kb(lang))


@router.message(Checkout.receipt, F.photo)
async def got_receipt(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    lang: str | None,
    bot: Bot,
) -> None:
    settings = get_settings()
    try:
        data = await download_photo(bot, message)
        path = await save_image(data, settings.upload_dir, RECEIPTS_SUBDIR, settings.max_upload_mb)
    except ImageError as exc:
        await message.answer(t(f"image_err_{exc.code}", lang))
        return
    await state.update_data(receipt=path)
    await _show_confirm(message, state, session, user, lang)


@router.message(Checkout.receipt, F.text.in_(labels("btn_skip")))
async def skip_receipt(
    message: Message, state: FSMContext, session: AsyncSession, user: User, lang: str | None
) -> None:
    if get_settings().require_receipt:
        await message.answer(t("receipt_required", lang))
        return
    await state.update_data(receipt=None)
    await _show_confirm(message, state, session, user, lang)


@router.message(StateFilter(Checkout.receipt))
async def receipt_wrong_input(message: Message, lang: str | None) -> None:
    await message.answer(t("receipt_photo_needed", lang))


@router.message(StateFilter(Checkout.name, Checkout.phone, Checkout.address, Checkout.comment))
async def wrong_input(message: Message, lang: str | None) -> None:
    await message.answer(t("text_needed", lang))


@router.callback_query(Checkout.confirm, ConfirmCB.filter())
async def confirm_order(
    call: CallbackQuery,
    callback_data: ConfirmCB,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    lang: str | None,
    bots: dict[str, Bot],
) -> None:
    await call.answer()
    message = call.message if isinstance(call.message, Message) else None
    if message is None:
        return
    if not callback_data.ok:
        await state.clear()
        await message.edit_text(t("order_cancelled", lang))
        await message.answer(t("back_to_menu", lang), reply_markup=main_menu(lang))
        return
    d = await state.get_data()
    try:
        order = await order_service.create_order(
            session,
            user,
            source="classic",
            customer_name=d["name"],
            phone=d["phone"],
            address=d["address"],
            comment=d.get("comment"),
            receipt_path=d.get("receipt"),
        )
    except order_service.EmptyCartError:
        await state.clear()
        await message.edit_text(t("cart_empty", lang))
        await message.answer(t("back_to_menu", lang), reply_markup=main_menu(lang))
        return
    await users.set_phone(session, user, order.phone)
    await state.clear()
    await message.edit_text(t("order_created", lang, id=order.id))
    await message.answer(t("order_thanks", lang), reply_markup=main_menu(lang))
    full = await order_service.get_order(session, order.id)
    if full is not None:
        await notify_admins_new_order(
            bots, get_settings().admin_ids, full, reply_markup=new_order_kb(full.id)
        )


@router.callback_query(ConfirmCB.filter())
async def confirm_stale(call: CallbackQuery, lang: str | None) -> None:
    await call.answer(t("confirm_stale", lang), show_alert=True)
