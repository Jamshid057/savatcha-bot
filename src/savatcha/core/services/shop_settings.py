from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.core.config import Settings
from savatcha.core.db.models import Setting

KEYS = ("shop_name", "shop_phone", "work_hours", "notify_admin_ids")


def defaults(settings: Settings) -> dict[str, object]:
    return {
        "shop_name": settings.shop_name,
        "shop_phone": settings.shop_phone,
        "work_hours": settings.shop_hours,
        "notify_admin_ids": [],  # bo'sh = hamma ADMIN_IDS ga
    }


async def get_all(session: AsyncSession, settings: Settings) -> dict[str, object]:
    values = defaults(settings)
    for row in (await session.scalars(select(Setting))).all():
        if row.key in KEYS:
            values[row.key] = row.value
    return values


async def update(session: AsyncSession, changes: dict[str, object]) -> None:
    for key, value in changes.items():
        if key not in KEYS:
            raise ValueError(f"unknown setting {key!r}")
        row = await session.get(Setting, key)
        if row is None:
            session.add(Setting(key=key, value=value))
        else:
            row.value = value
    await session.commit()


async def notification_recipients(session: AsyncSession, settings: Settings) -> list[int]:
    """Yangi buyurtma xabari kimga boradi: sozlamadagi adminlar (faqat ADMIN_IDS ichidagilar)."""
    values = await get_all(session, settings)
    chosen = [int(i) for i in values["notify_admin_ids"] if int(i) in settings.admin_ids]  # type: ignore[union-attr]
    return chosen or list(settings.admin_ids)
