from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from savatcha.core.db.models import ORDER_SOURCES, ORDER_STATUSES, Order
from savatcha.core.services import orders as order_service
from savatcha.core.services.stats import range_bounds

SORT_FIELDS = ("id", "created_at", "total", "status")
EXPORT_LIMIT = 10_000


@dataclass
class OrderFilter:
    status: str | None = None
    source: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    q: str | None = None


class InvalidFilter(ValueError):
    pass


def _conditions(f: OrderFilter) -> list:
    conds = []
    if f.status:
        if f.status not in ORDER_STATUSES:
            raise InvalidFilter("status")
        conds.append(Order.status == f.status)
    if f.source:
        if f.source not in ORDER_SOURCES:
            raise InvalidFilter("source")
        conds.append(Order.source == f.source)
    if f.date_from or f.date_to:
        start, _ = range_bounds(f.date_from or f.date_to, f.date_from or f.date_to)  # type: ignore[arg-type]
        _, end = range_bounds(f.date_to or f.date_from, f.date_to or f.date_from)  # type: ignore[arg-type]
        if f.date_from:
            conds.append(Order.created_at >= start)
        if f.date_to:
            conds.append(Order.created_at < end)
    if f.q and f.q.strip():
        text = f.q.strip()
        pattern = "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        parts = [
            Order.customer_name.ilike(pattern, escape="\\"),
            Order.phone.ilike(pattern, escape="\\"),
        ]
        if text.lstrip("#").isdigit():
            parts.append(Order.id == int(text.lstrip("#")))
        conds.append(or_(*parts))
    return conds


async def search_orders(
    session: AsyncSession,
    f: OrderFilter,
    *,
    sort: str = "id",
    direction: str = "desc",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Order], int]:
    if sort not in SORT_FIELDS:
        sort = "id"
    conds = _conditions(f)
    total = await session.scalar(select(func.count(Order.id)).where(*conds)) or 0
    col = getattr(Order, sort)
    stmt = (
        select(Order)
        .where(*conds)
        .options(selectinload(Order.items), selectinload(Order.history))
        .execution_options(populate_existing=True)
        .order_by(col.desc() if direction == "desc" else col.asc(), Order.id.desc())
        .limit(per_page)
        .offset((max(1, page) - 1) * per_page)
    )
    return list((await session.scalars(stmt)).all()), int(total)


async def export_orders(session: AsyncSession, f: OrderFilter) -> list[Order]:
    orders, _ = await search_orders(session, f, per_page=EXPORT_LIMIT)
    return orders


async def bulk_change_status(
    session: AsyncSession, ids: list[int], new_status: str, by_tg_id: int
) -> tuple[list[Order], list[dict[str, object]]]:
    """Har bir buyurtma alohida tekshiriladi; ruxsat etilmaganlar `failed` da qaytadi."""
    updated: list[Order] = []
    failed: list[dict[str, object]] = []
    for order_id in dict.fromkeys(ids):
        order = await order_service.get_order(session, order_id)
        if order is None:
            failed.append({"id": order_id, "reason": "not_found"})
            continue
        try:
            await order_service.change_status(session, order, new_status, by_tg_id)
        except order_service.InvalidTransition:
            failed.append({"id": order_id, "reason": "invalid_transition"})
        else:
            updated.append(order)
    return updated, failed
