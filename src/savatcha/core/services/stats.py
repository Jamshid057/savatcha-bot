from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import Date, Integer, and_, cast, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.core.db.models import (
    ORDER_SOURCES,
    ORDER_STATUSES,
    Category,
    Order,
    OrderItem,
    Product,
    User,
)

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


# ---------------------------------------------------------------------------
# Veb admin statistikasi (C qism). Hamma agregat SQL da; kunlar Asia/Tashkent bo'yicha.
# ---------------------------------------------------------------------------
_UTC_OFFSET_HOURS = 5  # Asia/Tashkent: DST yo'q, doimiy UTC+5


def _is_pg(session: AsyncSession) -> bool:
    return session.get_bind().dialect.name == "postgresql"


def local_day(session: AsyncSession, column):  # noqa: ANN001, ANN201
    if _is_pg(session):
        return cast(func.timezone("Asia/Tashkent", column), Date)
    return func.date(column, f"+{_UTC_OFFSET_HOURS} hours")


def local_hour(session: AsyncSession, column):  # noqa: ANN001, ANN201
    if _is_pg(session):
        return cast(func.extract("hour", func.timezone("Asia/Tashkent", column)), Integer)
    return cast(func.strftime("%H", column, f"+{_UTC_OFFSET_HOURS} hours"), Integer)


def _as_date(value: object) -> date:
    return (
        value
        if isinstance(value, date) and not isinstance(value, datetime)
        else date.fromisoformat(str(value)[:10])
    )


def range_bounds(d_from: date, d_to: date) -> tuple[datetime, datetime]:
    """[d_from 00:00, d_to+1 00:00) Toshkent vaqti, UTC da."""
    return day_bounds(d_from)[0], day_bounds(d_to)[1]


def days_in(d_from: date, d_to: date) -> list[date]:
    return [d_from + timedelta(days=i) for i in range((d_to - d_from).days + 1)]


def _money(value: object) -> Decimal:
    return Decimal(str(value or 0))


def _pct(current: Decimal | int, previous: Decimal | int) -> float | None:
    if not previous:
        return 0.0 if not current else None
    return round(float((Decimal(current) - Decimal(previous)) / Decimal(previous) * 100), 1)


async def _kpis(
    session: AsyncSession, d_from: date, d_to: date, statuses: Sequence[str]
) -> dict[str, Decimal | int]:
    start, end = range_bounds(d_from, d_to)
    count, revenue = await orders_summary(session, start, end, statuses)
    new_customers = await session.scalar(
        select(func.count(User.id)).where(User.created_at >= start, User.created_at < end)
    )
    return {
        "orders": count,
        "revenue": revenue,
        "avg_check": (revenue / count).quantize(Decimal("0.01")) if count else Decimal(0),
        "new_customers": int(new_customers or 0),
    }


async def summary(
    session: AsyncSession, d_from: date, d_to: date, statuses: Sequence[str]
) -> dict[str, object]:
    """KPI + oldingi (teng uzunlikdagi) davr bilan taqqoslash."""
    length = (d_to - d_from).days + 1
    prev_to = d_from - timedelta(days=1)
    prev_from = prev_to - timedelta(days=length - 1)
    current = await _kpis(session, d_from, d_to, statuses)
    previous = await _kpis(session, prev_from, prev_to, statuses)
    pending = await session.scalar(select(func.count(Order.id)).where(Order.status == "new"))
    return {
        "period": {"from": d_from, "to": d_to, "prev_from": prev_from, "prev_to": prev_to},
        "current": current,
        "previous": previous,
        "change": {k: _pct(current[k], previous[k]) for k in current},
        "pending": int(pending or 0),
    }


async def sales_by_day(
    session: AsyncSession, d_from: date, d_to: date, statuses: Sequence[str]
) -> list[dict[str, object]]:
    start, end = range_bounds(d_from, d_to)
    day = local_day(session, Order.created_at)
    rows = (
        await session.execute(
            select(day, func.count(Order.id), func.coalesce(func.sum(Order.total), 0))
            .where(
                Order.created_at >= start, Order.created_at < end, Order.status.in_(list(statuses))
            )
            .group_by(day)
        )
    ).all()
    found = {_as_date(r[0]): (int(r[1]), _money(r[2])) for r in rows}
    return [
        {
            "date": d,
            "orders": found.get(d, (0, Decimal(0)))[0],
            "revenue": found.get(d, (0, Decimal(0)))[1],
        }
        for d in days_in(d_from, d_to)
    ]


async def orders_by_status(
    session: AsyncSession, d_from: date, d_to: date
) -> list[dict[str, object]]:
    start, end = range_bounds(d_from, d_to)
    rows = (
        await session.execute(
            select(Order.status, func.count(Order.id))
            .where(Order.created_at >= start, Order.created_at < end)
            .group_by(Order.status)
        )
    ).all()
    found = {r[0]: int(r[1]) for r in rows}
    return [{"status": s, "orders": found.get(s, 0)} for s in ORDER_STATUSES]


async def by_source(
    session: AsyncSession, d_from: date, d_to: date, statuses: Sequence[str]
) -> list[dict[str, object]]:
    start, end = range_bounds(d_from, d_to)
    rows = (
        await session.execute(
            select(Order.source, func.count(Order.id), func.coalesce(func.sum(Order.total), 0))
            .where(
                Order.created_at >= start, Order.created_at < end, Order.status.in_(list(statuses))
            )
            .group_by(Order.source)
        )
    ).all()
    found = {r[0]: (int(r[1]), _money(r[2])) for r in rows}
    return [
        {
            "source": s,
            "orders": found.get(s, (0, Decimal(0)))[0],
            "revenue": found.get(s, (0, Decimal(0)))[1],
        }
        for s in ORDER_SOURCES
    ]


async def by_category(
    session: AsyncSession, d_from: date, d_to: date, statuses: Sequence[str]
) -> list[dict[str, object]]:
    start, end = range_bounds(d_from, d_to)
    revenue = func.sum(OrderItem.price_snapshot * OrderItem.quantity)
    rows = (
        await session.execute(
            select(Category.id, Category.name_uz, Category.name_ru, revenue)
            .join(Product, Product.category_id == Category.id)
            .join(OrderItem, OrderItem.product_id == Product.id)
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                Order.created_at >= start, Order.created_at < end, Order.status.in_(list(statuses))
            )
            .group_by(Category.id, Category.name_uz, Category.name_ru)
            .order_by(revenue.desc(), Category.id)
        )
    ).all()
    return [
        {"category_id": r[0], "name_uz": r[1], "name_ru": r[2], "revenue": _money(r[3])}
        for r in rows
    ]


async def by_hour(
    session: AsyncSession, d_from: date, d_to: date, statuses: Sequence[str]
) -> list[dict[str, int]]:
    start, end = range_bounds(d_from, d_to)
    hour = local_hour(session, Order.created_at)
    rows = (
        await session.execute(
            select(hour, func.count(Order.id))
            .where(
                Order.created_at >= start, Order.created_at < end, Order.status.in_(list(statuses))
            )
            .group_by(hour)
        )
    ).all()
    found = {int(r[0]): int(r[1]) for r in rows}
    return [{"hour": h, "orders": found.get(h, 0)} for h in range(24)]


async def top_products(
    session: AsyncSession,
    statuses: Sequence[str],
    *,
    by: str = "qty",
    limit: int = 10,
    d_from: date | None = None,
    d_to: date | None = None,
) -> list[dict[str, object]]:
    qty = func.sum(OrderItem.quantity)
    revenue = func.sum(OrderItem.price_snapshot * OrderItem.quantity)
    metric = revenue if by == "revenue" else qty
    stmt = (
        select(Product.id, Product.name_uz, Product.name_ru, qty, revenue)
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.status.in_(list(statuses)))
        .group_by(Product.id, Product.name_uz, Product.name_ru)
        .order_by(metric.desc(), Product.id)
        .limit(limit)
    )
    if d_from and d_to:
        start, end = range_bounds(d_from, d_to)
        stmt = stmt.where(Order.created_at >= start, Order.created_at < end)
    rows = (await session.execute(stmt)).all()
    return [
        {
            "product_id": r[0],
            "name_uz": r[1],
            "name_ru": r[2],
            "quantity": int(r[3]),
            "revenue": _money(r[4]),
        }
        for r in rows
    ]


async def slow_products(
    session: AsyncSession, statuses: Sequence[str], *, days: int = 30, now: datetime | None = None
) -> list[dict[str, object]]:
    """Oxirgi `days` kunda bir marta ham sotilmagan (arxivlanmagan) mahsulotlar."""
    since = (now or datetime.now(UTC)) - timedelta(days=days)
    sold = exists().where(
        and_(
            OrderItem.product_id == Product.id,
            OrderItem.order_id == Order.id,
            Order.created_at >= since,
            Order.status.in_(list(statuses)),
        )
    )
    rows = (
        await session.execute(
            select(Product.id, Product.name_uz, Product.name_ru, Product.price)
            .where(Product.is_archived.is_(False), ~sold)
            .order_by(Product.id)
        )
    ).all()
    return [
        {"product_id": r[0], "name_uz": r[1], "name_ru": r[2], "price": _money(r[3])} for r in rows
    ]


async def product_detail(
    session: AsyncSession, product_id: int, d_from: date, d_to: date, statuses: Sequence[str]
) -> dict[str, object]:
    start, end = range_bounds(d_from, d_to)
    day = local_day(session, Order.created_at)
    qty = func.sum(OrderItem.quantity)
    revenue = func.sum(OrderItem.price_snapshot * OrderItem.quantity)
    rows = (
        await session.execute(
            select(day, qty, revenue)
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                OrderItem.product_id == product_id,
                Order.created_at >= start,
                Order.created_at < end,
                Order.status.in_(list(statuses)),
            )
            .group_by(day)
        )
    ).all()
    found = {_as_date(r[0]): (int(r[1]), _money(r[2])) for r in rows}
    series = [
        {
            "date": d,
            "quantity": found.get(d, (0, Decimal(0)))[0],
            "revenue": found.get(d, (0, Decimal(0)))[1],
        }
        for d in days_in(d_from, d_to)
    ]
    return {
        "product_id": product_id,
        "total_quantity": sum(int(p["quantity"]) for p in series),  # type: ignore[arg-type]
        "total_revenue": sum((p["revenue"] for p in series), Decimal(0)),  # type: ignore[arg-type]
        "series": series,
    }


async def top_customers(
    session: AsyncSession, statuses: Sequence[str], *, limit: int = 10
) -> dict[str, object]:
    spent = func.sum(Order.total)
    rows = (
        await session.execute(
            select(User.id, User.full_name, User.username, func.count(Order.id), spent)
            .join(Order, Order.user_id == User.id)
            .where(Order.status.in_(list(statuses)))
            .group_by(User.id, User.full_name, User.username)
            .order_by(spent.desc(), User.id)
        )
    ).all()
    buyers = len(rows)
    repeat = sum(1 for r in rows if r[3] >= 2)
    return {
        "customers": [
            {
                "user_id": r[0],
                "full_name": r[1],
                "username": r[2],
                "orders": int(r[3]),
                "total_spent": _money(r[4]),
            }
            for r in rows[:limit]
        ],
        "buyers": buyers,
        "repeat_buyers": repeat,
        "repeat_share": round(repeat / buyers * 100, 1) if buyers else 0.0,
    }


async def new_customers_by_day(
    session: AsyncSession, d_from: date, d_to: date
) -> list[dict[str, object]]:
    start, end = range_bounds(d_from, d_to)
    day = local_day(session, User.created_at)
    rows = (
        await session.execute(
            select(day, func.count(User.id))
            .where(User.created_at >= start, User.created_at < end)
            .group_by(day)
        )
    ).all()
    found = {_as_date(r[0]): int(r[1]) for r in rows}
    return [{"date": d, "customers": found.get(d, 0)} for d in days_in(d_from, d_to)]
