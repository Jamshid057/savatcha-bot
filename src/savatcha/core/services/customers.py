from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.core.db.models import Order, User

SORT_FIELDS = ("full_name", "orders_count", "total_spent", "last_order_at", "created_at")


@dataclass
class CustomerRow:
    user: User
    orders_count: int
    total_spent: Decimal
    last_order_at: datetime | None


def _like(text: str) -> str:
    escaped = text.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _aggregate(statuses: Sequence[str]):  # noqa: ANN202
    return (
        select(
            Order.user_id.label("user_id"),
            func.count(Order.id).label("orders_count"),
            func.coalesce(
                func.sum(case((Order.status.in_(list(statuses)), Order.total), else_=0)), 0
            ).label("total_spent"),
            func.max(Order.created_at).label("last_order_at"),
        )
        .group_by(Order.user_id)
        .subquery()
    )


async def list_customers(
    session: AsyncSession,
    statuses: Sequence[str],
    *,
    search: str | None = None,
    sort: str = "created_at",
    direction: str = "desc",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[CustomerRow], int]:
    if sort not in SORT_FIELDS:
        sort = "created_at"
    agg = _aggregate(statuses)
    orders_count = func.coalesce(agg.c.orders_count, 0)
    total_spent = func.coalesce(agg.c.total_spent, 0)
    sort_col = {
        "full_name": User.full_name,
        "orders_count": orders_count,
        "total_spent": total_spent,
        "last_order_at": agg.c.last_order_at,
        "created_at": User.created_at,
    }[sort]
    stmt = select(User, orders_count, total_spent, agg.c.last_order_at).outerjoin(
        agg, agg.c.user_id == User.id
    )
    count_stmt = select(func.count(User.id))
    if search and search.strip():
        pattern = _like(search)
        cond = or_(
            User.full_name.ilike(pattern, escape="\\"),
            User.username.ilike(pattern, escape="\\"),
            User.phone.ilike(pattern, escape="\\"),
        )
        stmt, count_stmt = stmt.where(cond), count_stmt.where(cond)
    order = sort_col.desc() if direction == "desc" else sort_col.asc()
    stmt = stmt.order_by(order, User.id).limit(per_page).offset((max(1, page) - 1) * per_page)
    rows = (await session.execute(stmt)).all()
    total = await session.scalar(count_stmt) or 0
    return [CustomerRow(r[0], int(r[1]), Decimal(str(r[2] or 0)), r[3]) for r in rows], int(total)


async def get_customer(
    session: AsyncSession, user_id: int, statuses: Sequence[str]
) -> CustomerRow | None:
    agg = _aggregate(statuses)
    row = (
        await session.execute(
            select(
                User,
                func.coalesce(agg.c.orders_count, 0),
                func.coalesce(agg.c.total_spent, 0),
                agg.c.last_order_at,
            )
            .outerjoin(agg, agg.c.user_id == User.id)
            .where(User.id == user_id)
        )
    ).first()
    if row is None:
        return None
    return CustomerRow(row[0], int(row[1]), Decimal(str(row[2] or 0)), row[3])
