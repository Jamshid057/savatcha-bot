from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.bot.keyboards.cart import CartCB, cart_kb
from savatcha.bot.utils import safe_edit
from savatcha.core.db.models import User
from savatcha.core.i18n import t
from savatcha.core.services import cart as cart_service
from savatcha.core.services.catalog import localized
from savatcha.core.utils.money import format_price

router = Router(name="cart")


def cart_text(cart: cart_service.Cart, lang: str | None) -> str:
    lines = [t("cart_title", lang), ""]
    for i, line in enumerate(cart.lines, 1):
        name = localized(line.product, "name", lang)
        lines.append(f"{i}. {name} × {line.quantity} = {format_price(line.subtotal, lang)}")
    lines += ["", t("order_total", lang, total=format_price(cart.total, lang))]
    if cart.removed:
        names = ", ".join(localized(p, "name", lang) for p in cart.removed)
        lines += ["", t("cart_removed", lang, names=names)]
    return "\n".join(lines)


async def show_cart(message: Message, session: AsyncSession, user: User, lang: str | None) -> None:
    cart = await cart_service.get_cart(session, user.id)
    if not cart.lines:
        await message.answer(t("cart_empty", lang))
        return
    await message.answer(cart_text(cart, lang), reply_markup=cart_kb(cart, lang))


async def _rerender(
    call: CallbackQuery, session: AsyncSession, user: User, lang: str | None
) -> None:
    cart = await cart_service.get_cart(session, user.id)
    if not cart.lines:
        await safe_edit(call.message, t("cart_empty", lang))
        return
    await safe_edit(call.message, cart_text(cart, lang), cart_kb(cart, lang))


@router.callback_query(CartCB.filter(F.act.in_({"inc", "dec", "del"})))
async def change_item(
    call: CallbackQuery,
    callback_data: CartCB,
    session: AsyncSession,
    user: User,
    lang: str | None,
) -> None:
    await call.answer()
    cart = await cart_service.get_cart(session, user.id)
    line = next((ln for ln in cart.lines if ln.product.id == callback_data.id), None)
    if line is not None:
        delta = {"inc": line.quantity + 1, "dec": line.quantity - 1, "del": 0}
        try:
            await cart_service.set_quantity(
                session, user.id, line.product.id, delta[callback_data.act]
            )
        except cart_service.ProductUnavailable:
            pass
    await _rerender(call, session, user, lang)


@router.callback_query(CartCB.filter(F.act == "clear"))
async def clear(call: CallbackQuery, session: AsyncSession, user: User, lang: str | None) -> None:
    await call.answer()
    await cart_service.clear_cart(session, user.id)
    await _rerender(call, session, user, lang)
