from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.core.config import get_settings
from savatcha.core.db.models import Product
from savatcha.core.i18n import t
from savatcha.core.services import catalog
from savatcha.core.services.files import resolve_path
from savatcha.core.utils.money import format_price

CAPTION_LIMIT = 1000


def total_pages(total: int, per_page: int = catalog.PAGE_SIZE) -> int:
    return max(1, -(-total // per_page))


async def safe_edit(
    message: Message | object, text: str, reply_markup: InlineKeyboardMarkup | None = None
) -> None:
    """edit_text; 'message is not modified' xatosi va rasmli xabarlar jim o'tkaziladi."""
    if not isinstance(message, Message):
        return
    try:
        if message.photo:
            await message.edit_caption(caption=text[:CAPTION_LIMIT], reply_markup=reply_markup)
        else:
            await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "not modified" not in str(exc):
            raise


def product_text(product: Product, lang: str | None) -> str:
    name = catalog.localized(product, "name", lang)
    desc = catalog.localized(product, "description", lang)
    status = t("in_stock" if product.is_available else "out_of_stock", lang)
    parts = [name]
    if desc:
        parts.append(desc[:700])
    parts.append(f"💰 {format_price(product.price, lang)}\n{status}")
    return "\n\n".join(parts)[:CAPTION_LIMIT]


async def send_product(
    message: Message,
    session: AsyncSession,
    product: Product,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Mahsulot kartasi: rasm bo'lsa rasm bilan (tg_file_id keshlanadi), bo'lmasa matn."""
    path = (
        resolve_path(get_settings().upload_dir, product.image_path) if product.image_path else None
    )
    if product.tg_file_id:
        try:
            await message.answer_photo(product.tg_file_id, caption=text, reply_markup=reply_markup)
            return
        except TelegramBadRequest:
            product.tg_file_id = None  # eskirgan id: diskdan qayta yuboramiz
    if path is None:
        await message.answer(text, reply_markup=reply_markup)
        return
    sent = await message.answer_photo(FSInputFile(path), caption=text, reply_markup=reply_markup)
    if sent.photo:
        await catalog.set_tg_file_id(session, product, sent.photo[-1].file_id)


async def download_photo(bot: Bot, message: Message) -> bytes:
    assert message.photo
    buf = await bot.download(message.photo[-1])
    assert buf is not None
    return buf.getvalue()
