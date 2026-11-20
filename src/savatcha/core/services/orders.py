from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from savatcha.core.db.models import (
    ORDER_SOURCES,
    ORDER_STATUSES,
    Order,
    OrderItem,
    OrderStatusHistory,
    User,
)
from savatcha.core.services import cart as cart_service
from savatcha.core.utils.phone import normalize_phone

ORDERS_PAGE_SIZE = 5
_LOAD_RELATED = (selectinload(Order.items), selectinload(Order.history))

TRANSITIONS: dict[str, tuple[str, ...]] = {
    "new": ("accepted", "cancelled"),
    "accepted": ("delivering", "cancelled"),
    "delivering": ("done", "cancelled"),
    "done": (),
    "cancelled": (),
}
STATUS_GROUPS: dict[str, tuple[str, ...]] = {
    "new": ("new",),
    "active": ("accepted", "delivering"),
    "done": ("done",),
    "cancelled": ("cancelled",),
}


class OrderError(Exception):
    pass


class EmptyCartError(OrderError):
    pass


class InvalidPhone(OrderError):
    pass


class InvalidTransition(OrderError):
    pass


async def create_order(
    session: AsyncSession,
    user: User,
    *,
    source: str,
    customer_name: str,
    phone: str,
    address: str,
    comment: str | None,
    receipt_path: str | None,
) -> Order:
    """Savatdan buyurtma yaratadi: nom/narx snapshot, holat tarixi, savat tozalanadi."""
    if source not in ORDER_SOURCES:
        raise OrderError(f"unknown source {source!r}")
    normalized = normalize_phone(phone)
    if normalized is None:
        raise InvalidPhone
    cart = await cart_service.get_cart(session, user.id)
    if not cart.lines:
        raise EmptyCartError
    order = Order(
        user_id=user.id,
        source=source,
        status="new",
        customer_name=customer_name.strip(),
        phone=normalized,
        address=address.strip(),
        comment=(comment or "").strip() or None,
        receipt_path=receipt_path,
        total=cart.total,
        items=[
            OrderItem(
                product_id=line.product.id,
                name_snapshot=line.product.name_uz,
                price_snapshot=line.product.price,
                quantity=line.quantity,
            )
            for line in cart.lines
        ],
    )
    session.add(order)
    await session.flush()
    session.add(OrderStatusHistory(order_id=order.id, from_status=None, to_status="new"))
    await cart_service.clear_cart(session, user.id)  # commit shu yerda
    return order


async def get_order(
    session: AsyncSession, order_id: int, *, user_id: int | None = None
) -> Order | None:
    stmt = (
        select(Order)
        .where(Order.id == order_id)
        .options(*_LOAD_RELATED)
        .execution_options(populate_existing=True)  # sessiyada yaratilgan obyekt ham to'ldirilsin
    )
    if user_id is not None:
        stmt = stmt.where(Order.user_id == user_id)
    return await session.scalar(stmt)


async def change_status(
    session: AsyncSession, order: Order, new_status: str, by_tg_id: int | None
) -> None:
    if new_status not in ORDER_STATUSES or new_status not in TRANSITIONS.get(order.status, ()):
        raise InvalidTransition(f"{order.status} -> {new_status}")
    session.add(
        OrderStatusHistory(
            order_id=order.id,
            from_status=order.status,
            to_status=new_status,
            changed_by_tg_id=by_tg_id,
        )
    )
    order.status = new_status
    await session.commit()


async def list_user_orders(session: AsyncSession, user_id: int, limit: int = 10) -> list[Order]:
    stmt = (
        select(Order)
        .where(Order.user_id == user_id)
        .options(*_LOAD_RELATED)
        .execution_options(populate_existing=True)
        .order_by(Order.id.desc())
        .limit(limit)
    )
    return list((await session.scalars(stmt)).all())


async def list_orders(
    session: AsyncSession,
    *,
    group: str | None = None,
    status: str | None = None,
    page: int = 1,
    per_page: int = ORDERS_PAGE_SIZE,
) -> tuple[list[Order], int]:
    conds = []
    if group is not None:
        conds.append(Order.status.in_(STATUS_GROUPS[group]))
    if status is not None:
        conds.append(Order.status == status)
    total = await session.scalar(select(func.count()).select_from(Order).where(*conds)) or 0
    stmt = (
        select(Order)
        .where(*conds)
        .options(*_LOAD_RELATED)
        .execution_options(populate_existing=True)
        .order_by(Order.id.desc())
        .limit(per_page)
        .offset((max(1, page) - 1) * per_page)
    )
    return list((await session.scalars(stmt)).all()), total
