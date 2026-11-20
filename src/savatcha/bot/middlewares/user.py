from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.core.repo import users


class UserMiddleware(BaseMiddleware):
    """Foydalanuvchini DB dan oladi/yaratadi va handlerga `user` hamda `lang` beradi."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        if tg_user is not None and not tg_user.is_bot:
            session: AsyncSession = data["session"]
            user = await users.get_or_create(
                session, tg_user.id, tg_user.full_name, tg_user.username
            )
            data["user"] = user
            data["lang"] = user.lang
        return await handler(event, data)
