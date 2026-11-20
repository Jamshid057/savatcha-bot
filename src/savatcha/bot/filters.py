from aiogram import Router
from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject, User

from savatcha.core.config import get_settings


class IsAdmin(BaseFilter):
    """Faqat ADMIN_IDS dagi foydalanuvchilar. Har handlerda takrorlanmaydi: router darajasida."""

    async def __call__(self, event: TelegramObject, event_from_user: User | None = None) -> bool:
        return event_from_user is not None and event_from_user.id in get_settings().admin_ids


def admin_router(name: str) -> Router:
    router = Router(name=name)
    router.message.filter(IsAdmin())
    router.callback_query.filter(IsAdmin())
    return router
