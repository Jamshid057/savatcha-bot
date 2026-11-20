import logging
from collections.abc import Iterable, Mapping

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardMarkup

from savatcha.core.db.models import Order
from savatcha.core.i18n import t
from savatcha.core.services.formatting import format_order_text, status_label

log = logging.getLogger(__name__)

Bots = Mapping[str, Bot]  # orders.source -> shu manba boti


async def notify_admins_new_order(
    bots: Bots,
    admin_ids: Iterable[int],
    order: Order,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    bot = bots.get(order.source)
    if bot is None:
        log.warning("Order %s: '%s' manbasi uchun bot yo'q", order.id, order.source)
        return
    text = t("notify_new_order", None) + "\n\n" + format_order_text(order, None, admin=True)
    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, text, reply_markup=reply_markup)
        except TelegramAPIError:
            log.exception("Adminga (%s) xabar yuborilmadi", admin_id)


async def notify_user_status_changed(
    bots: Bots, order: Order, user_tg_id: int, lang: str | None
) -> None:
    bot = bots.get(order.source)
    if bot is None:
        log.warning("Order %s: '%s' manbasi uchun bot yo'q", order.id, order.source)
        return
    text = t("notify_status", lang, id=order.id, status=status_label(order.status, lang))
    try:
        await bot.send_message(user_tg_id, text)
    except TelegramAPIError:
        log.exception("Mijozga (%s) xabar yuborilmadi", user_tg_id)
