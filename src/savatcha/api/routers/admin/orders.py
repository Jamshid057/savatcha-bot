from aiogram import Bot
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.api.deps import get_bots, get_session, require_admin, settings_dep
from savatcha.api.schemas import OrderOut, OrderPage, StatusIn, order_out
from savatcha.api.uploads import file_response
from savatcha.core.config import Settings
from savatcha.core.db.models import ORDER_STATUSES, User
from savatcha.core.services import orders as order_service
from savatcha.core.services.notify import notify_user_status_changed

router = APIRouter(prefix="/orders", dependencies=[Depends(require_admin)])


@router.get("", response_model=OrderPage)
async def list_orders(
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    if status is not None and status not in ORDER_STATUSES:
        raise HTTPException(422, "invalid_status")
    items, total = await order_service.list_orders(
        session, status=status, page=page, per_page=per_page
    )
    return OrderPage(
        items=[order_out(o) for o in items],
        total=total,
        page=page,
        pages=max(1, -(-total // per_page)),
    )


async def _get(session: AsyncSession, order_id: int):
    order = await order_service.get_order(session, order_id)
    if order is None:
        raise HTTPException(404, "not_found")
    return order


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(order_id: int, session: AsyncSession = Depends(get_session)):
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
    try:
        await order_service.change_status(session, order, body.status, admin.tg_id)
    except order_service.InvalidTransition as exc:
        raise HTTPException(409, "invalid_transition") from exc
    customer = await session.get(User, order.user_id)
    if customer is not None:
        await notify_user_status_changed(bots, order, customer.tg_id, customer.lang)
    return order_out(await _get(session, order_id))


@router.get("/{order_id}/receipt")
async def receipt(
    order_id: int,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_dep),
):
    order = await _get(session, order_id)
    return file_response(settings, order.receipt_path)
