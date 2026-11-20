from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.core.db.models import Order

TASHKENT = ZoneInfo("Asia/Tashkent")


def day_bounds(day: date) -> tuple[datetime, datetime]:
    """Toshkent vaqti bo'yicha kun chegarasi (UTC da): [start, end)."""
    start = datetime.combine(day, time.min, tzinfo=TASHKENT)
    return start.astimezone(UTC), (start + timedelta(days=1)).astimezone(UTC)


def today_tashkent() -> date:
    return datetime.now(TASHKENT).date()


async def orders_summary(
    session: AsyncSession, start: datetime, end: datetime, statuses: Sequence[str]
) -> tuple[int, Decimal]:
    """[start, end) oralig'ida `statuses` dagi buyurtmalar soni va tushum."""
    row = (
        await session.execute(
            select(func.count(Order.id), func.coalesce(func.sum(Order.total), 0)).where(
                Order.created_at >= start,
                Order.created_at < end,
                Order.status.in_(list(statuses)),
            )
        )
    ).one()
    return int(row[0]), Decimal(row[1])


async def today_and_week(
    session: AsyncSession, statuses: Sequence[str], today: date | None = None
) -> dict[str, tuple[int, Decimal]]:
    """`/stats` uchun: bugun va oxirgi 7 kun (bugun bilan)."""
    today = today or today_tashkent()
    day_start, day_end = day_bounds(today)
    week_start, _ = day_bounds(today - timedelta(days=6))
    return {
        "today": await orders_summary(session, day_start, day_end, statuses),
        "week": await orders_summary(session, week_start, day_end, statuses),
    }
