from datetime import date

from aiogram import Bot
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.api.deps import get_bots, get_session, require_admin, settings_dep
from savatcha.api.schemas import BulkStatusIn, OrderOut, OrderPage, StatusIn, order_out
from savatcha.api.uploads import file_response
from savatcha.core.config import Settings
from savatcha.core.db.models import ORDER_STATUSES, User
from savatcha.core.services import admin_orders, audit, csv_export
from savatcha.core.services import orders as order_service
from savatcha.core.services.notify import notify_user_status_changed

router = APIRouter(prefix="/orders")


def order_filter(
    status: str | None = None,
    source: str | None = None,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    q: str | None = Query(default=None, max_length=100),
) -> admin_orders.OrderFilter:
    return admin_orders.OrderFilter(status, source, date_from, date_to, q)


@router.get("", response_model=OrderPage)
async def list_orders(
    f: admin_orders.OrderFilter = Depends(order_filter),
    sort: str = "id",
    dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    try:
        items, total = await admin_orders.search_orders(
            session, f, sort=sort, direction=dir, page=page, per_page=per_page
        )
    except admin_orders.InvalidFilter as exc:
        raise HTTPException(422, f"invalid_{exc}") from exc
    return OrderPage(
        items=[order_out(o) for o in items],
        total=total,
        page=page,
        pages=max(1, -(-total // per_page)),
    )


@router.get("/export.csv")
async def export_csv(
    f: admin_orders.OrderFilter = Depends(order_filter),
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    try:
        orders = await admin_orders.export_orders(session, f)
    except admin_orders.InvalidFilter as exc:
        raise HTTPException(422, f"invalid_{exc}") from exc
    await audit.log_action(
        session, admin.tg_id, "export", "order", None, {"rows": len(orders), "status": f.status}
    )
    return Response(
        csv_export.orders_csv(orders),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="orders.csv"'},
    )


@router.patch("/bulk-status")
async def bulk_status(
    body: BulkStatusIn,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    bots: dict[str, Bot] = Depends(get_bots),
):
    if body.status not in ORDER_STATUSES:
        raise HTTPException(422, "invalid_status")
    updated, failed = await admin_orders.bulk_change_status(
        session, body.ids, body.status, admin.tg_id
    )
    for order in updated:
        customer = await session.get(User, order.user_id)
        if customer is not None:
            await notify_user_status_changed(bots, order, customer.tg_id, customer.lang)
    await audit.log_action(
        session,
        admin.tg_id,
        "status_change",
        "order",
        None,
        {"to": body.status, "updated": [o.id for o in updated], "failed": failed},
    )
    return {"updated": [o.id for o in updated], "failed": failed}


async def _get(session: AsyncSession, order_id: int):
    order = await order_service.get_order(session, order_id)
    if order is None:
        raise HTTPException(404, "not_found")
    return order


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: int,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return order_out(await _get(session, order_id))


@router.patch("/{order_id}/status", response_model=OrderOut)
async def change_status(
    order_id: int,
    body: StatusIn,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    bots: dict[str, Bot] = Depends(get_bots),
):
    order = await _get(session, order_id)
    previous = order.status
    try:
        await order_service.change_status(session, order, body.status, admin.tg_id)
    except order_service.InvalidTransition as exc:
        raise HTTPException(409, "invalid_transition") from exc
    await audit.log_action(
        session,
        admin.tg_id,
        "status_change",
        "order",
        order_id,
        {"from": previous, "to": body.status},
    )
    customer = await session.get(User, order.user_id)
    if customer is not None:
        await notify_user_status_changed(bots, order, customer.tg_id, customer.lang)
    return order_out(await _get(session, order_id))


@router.get("/{order_id}/receipt")
async def receipt(
    order_id: int,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_dep),
):
    order = await _get(session, order_id)
    return file_response(settings, order.receipt_path)
