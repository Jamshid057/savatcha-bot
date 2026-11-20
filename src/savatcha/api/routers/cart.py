from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.api.deps import current_user, get_session
from savatcha.api.schemas import CartOut, QuantityIn, cart_out
from savatcha.core.db.models import User
from savatcha.core.services import cart as cart_service

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("", response_model=CartOut)
async def get_cart(
    user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    return cart_out(await cart_service.get_cart(session, user.id))


@router.put("/items/{product_id}", response_model=CartOut)
async def set_item(
    product_id: int,
    body: QuantityIn,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        await cart_service.set_quantity(session, user.id, product_id, body.quantity)
    except cart_service.ProductUnavailable as exc:
        raise HTTPException(409, "product_unavailable") from exc
    return cart_out(await cart_service.get_cart(session, user.id))


@router.delete("", response_model=CartOut)
async def clear(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    await cart_service.clear_cart(session, user.id)
    return cart_out(await cart_service.get_cart(session, user.id))
