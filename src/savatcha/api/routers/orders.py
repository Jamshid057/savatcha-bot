from aiogram import Bot
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.api.deps import current_user, get_bots, get_session, settings_dep
from savatcha.api.limits import limiter
from savatcha.api.schemas import OrderOut, OrderPage, order_out
from savatcha.api.uploads import file_response, store_upload
from savatcha.core.config import Settings
from savatcha.core.db.models import User
from savatcha.core.repo import users
from savatcha.core.services import orders as order_service
from savatcha.core.services.files import RECEIPTS_SUBDIR
from savatcha.core.services.notify import notify_admins_new_order

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderOut, status_code=201)
@limiter.limit("10/minute")
async def create_order(
    request: Request,
    customer_name: str = Form(min_length=2, max_length=100),
    phone: str = Form(),
    address: str = Form(min_length=5, max_length=300),
    comment: str = Form(default="", max_length=500),
    receipt: UploadFile | None = File(default=None),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_dep),
    bots: dict[str, Bot] = Depends(get_bots),
):
    receipt_path = None
    if receipt is not None and receipt.filename:
        receipt_path = await store_upload(receipt, settings, RECEIPTS_SUBDIR)
    elif settings.require_receipt:
        raise HTTPException(422, "receipt_required")
    try:
        order = await order_service.create_order(
            session,
            user,
            source="miniapp",
            customer_name=customer_name,
            phone=phone,
            address=address,
            comment=comment,
            receipt_path=receipt_path,
        )
    except order_service.InvalidPhone as exc:
        raise HTTPException(422, "invalid_phone") from exc
    except order_service.EmptyCartError as exc:
        raise HTTPException(409, "empty_cart") from exc
    await users.set_phone(session, user, order.phone)
    full = await order_service.get_order(session, order.id)
    assert full is not None
    await notify_admins_new_order(bots, settings.admin_ids, full)
    return order_out(full)


@router.get("", response_model=OrderPage)
async def my_orders(
    page: int = Query(default=1, ge=1),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    items = await order_service.list_user_orders(session, user.id, limit=50)
    return OrderPage(items=[order_out(o) for o in items], total=len(items), page=1, pages=1)


async def _own_order(session: AsyncSession, user: User, order_id: int):
    order = await order_service.get_order(session, order_id, user_id=user.id)
    if order is None:
        raise HTTPException(404, "not_found")
    return order


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: int,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return order_out(await _own_order(session, user, order_id))


@router.get("/{order_id}/receipt")
async def my_receipt(
    order_id: int,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_dep),
):
    order = await _own_order(session, user, order_id)
    return file_response(settings, order.receipt_path)
