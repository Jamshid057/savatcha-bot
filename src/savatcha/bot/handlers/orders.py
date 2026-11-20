from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.bot.keyboards.common import MenuCB
from savatcha.bot.keyboards.orders import OrderViewCB, my_orders_kb, order_back_kb
from savatcha.bot.utils import safe_edit
from savatcha.core.db.models import User
from savatcha.core.i18n import t
from savatcha.core.services import orders as order_service
from savatcha.core.services.formatting import format_order_text
from savatcha.core.utils.text import split_text

router = Router(name="my_orders")


async def show_my_orders(
    message: Message, session: AsyncSession, user: User, lang: str | None
) -> None:
    orders = await order_service.list_user_orders(session, user.id)
    if not orders:
        await message.answer(t("orders_empty", lang))
        return
    await message.answer(t("orders_title", lang), reply_markup=my_orders_kb(orders, lang))


@router.callback_query(MenuCB.filter(F.act == "orders"))
async def back_to_orders(
    call: CallbackQuery, session: AsyncSession, user: User, lang: str | None
) -> None:
    await call.answer()
    orders = await order_service.list_user_orders(session, user.id)
    if orders:
        await safe_edit(call.message, t("orders_title", lang), my_orders_kb(orders, lang))


@router.callback_query(OrderViewCB.filter())
async def view_order(
    call: CallbackQuery,
    callback_data: OrderViewCB,
    session: AsyncSession,
    user: User,
    lang: str | None,
) -> None:
    order = await order_service.get_order(session, callback_data.id, user_id=user.id)
    if order is None:
        await call.answer(t("order_not_found", lang), show_alert=True)
        return
    await call.answer()
    # Telegram limiti: uzun buyurtma bo'laklarga bo'linadi, tugma oxirgisida.
    *head, last = split_text(format_order_text(order, lang))
    if isinstance(call.message, Message) and not head:
        await safe_edit(call.message, last, order_back_kb(lang))
    elif isinstance(call.message, Message):
        for part in head:
            await call.message.answer(part)
        await call.message.answer(last, reply_markup=order_back_kb(lang))
