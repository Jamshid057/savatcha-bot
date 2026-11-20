"""v2 uchun yengil bot: /start, /help va Mini App ochuvchi tugma (long polling)."""

import asyncio
import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
    WebAppInfo,
)

from savatcha.core.config import get_settings
from savatcha.core.i18n import t

log = logging.getLogger(__name__)
router = Router(name="gateway")


def _lang(message: Message) -> str:
    code = message.from_user.language_code if message.from_user else None
    return "ru" if code and code.startswith("ru") else "uz"


def open_app_kb(lang: str, url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("gateway_open", lang), web_app=WebAppInfo(url=url))]
        ]
    )


@router.message(CommandStart())
async def start(message: Message) -> None:
    lang = _lang(message)
    name = message.from_user.first_name if message.from_user else ""
    await message.answer(
        t("gateway_welcome", lang, name=name),
        reply_markup=open_app_kb(lang, get_settings().webapp_url),
    )


@router.message(Command("help"))
async def help_cmd(message: Message) -> None:
    lang = _lang(message)
    await message.answer(
        t("gateway_help", lang), reply_markup=open_app_kb(lang, get_settings().webapp_url)
    )


async def setup_menu_button(bot: Bot, url: str) -> None:
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(text=t("gateway_open", "uz"), web_app=WebAppInfo(url=url))
    )


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    if not settings.bot_token_app:
        raise SystemExit("BOT_TOKEN_APP .env da berilmagan")
    if not settings.webapp_url.startswith("https://"):
        raise SystemExit("WEBAPP_URL https:// bilan boshlanishi shart (Mini App faqat HTTPS da)")
    bot = Bot(settings.bot_token_app)
    dp = Dispatcher()
    dp.include_router(router)
    await setup_menu_button(bot, settings.webapp_url)
    log.info("Gateway bot ishga tushdi")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
