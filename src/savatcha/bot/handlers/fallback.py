from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from savatcha.core.i18n import t

router = Router(name="fallback")


@router.message(Command("admin", "stats"))
async def no_access(message: Message, lang: str | None) -> None:
    """Admin routerlari birinchi; bu yerga faqat admin bo'lmaganlar tushadi."""
    await message.answer(t("no_access", lang))
