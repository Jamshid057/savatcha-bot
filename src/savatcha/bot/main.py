import asyncio
import logging

from aiogram import Bot, Dispatcher

from savatcha.bot.handlers import admin, cart, catalog, checkout, fallback, menu, start
from savatcha.bot.handlers import orders as my_orders
from savatcha.bot.middlewares.db import DbSessionMiddleware
from savatcha.bot.middlewares.user import UserMiddleware
from savatcha.core.config import get_settings
from savatcha.core.db import models  # noqa: F401  (jadvallarni ro'yxatdan o'tkazadi)
from savatcha.core.db.base import make_engine, make_session_factory

log = logging.getLogger(__name__)


def build_dispatcher(session_factory, bot: Bot) -> Dispatcher:  # noqa: ANN001
    dp = Dispatcher()
    dp.update.middleware(DbSessionMiddleware(session_factory))
    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())
    dp["bots"] = {"classic": bot}
    # Tartib muhim: start/menu har qanday FSM holatini tozalaydi; admin FSM'dan oldin turadi.
    dp.include_routers(start.router, menu.router, *admin.routers)
    dp.include_routers(
        catalog.router, cart.router, my_orders.router, checkout.router, fallback.router
    )
    return dp


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    if not settings.bot_token_classic:
        raise SystemExit("BOT_TOKEN_CLASSIC .env da berilmagan")

    engine = make_engine(settings.database_url)
    bot = Bot(settings.bot_token_classic)
    dp = build_dispatcher(make_session_factory(engine), bot)

    log.info("Classic bot ishga tushdi")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
