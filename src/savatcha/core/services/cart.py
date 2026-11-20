from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.core.db.models import CartItem, Product

MAX_QTY = 99


class CartError(Exception):
    pass


class ProductUnavailable(CartError):
    pass


@dataclass
class CartLine:
    product: Product
    quantity: int

    @property
    def subtotal(self) -> Decimal:
        return self.product.price * self.quantity


@dataclass
class Cart:
    lines: list[CartLine] = field(default_factory=list)
    removed: list[Product] = field(default_factory=list)  # mavjud bo'lmay qolgani tozalandi

    @property
    def total(self) -> Decimal:
        return sum((line.subtotal for line in self.lines), Decimal(0))


def _orderable(product: Product | None) -> bool:
    return product is not None and product.is_available and not product.is_archived


async def get_cart(session: AsyncSession, user_id: int) -> Cart:
    """Savatni qaytaradi; mavjud bo'lmay qolgan mahsulotlar savatdan olib tashlanadi."""
    rows = (
        await session.execute(
            select(CartItem, Product)
            .join(Product, Product.id == CartItem.product_id)
            .where(CartItem.user_id == user_id)
            .order_by(CartItem.id)
        )
    ).all()
    cart = Cart()
    stale: list[int] = []
    for item, product in rows:
        if _orderable(product):
            cart.lines.append(CartLine(product, item.quantity))
        else:
            cart.removed.append(product)
            stale.append(item.id)
    if stale:
        await session.execute(delete(CartItem).where(CartItem.id.in_(stale)))
        await session.commit()
    return cart


async def _get_item(session: AsyncSession, user_id: int, product_id: int) -> CartItem | None:
    return await session.scalar(
        select(CartItem).where(CartItem.user_id == user_id, CartItem.product_id == product_id)
    )


async def set_quantity(session: AsyncSession, user_id: int, product_id: int, quantity: int) -> int:
    """Miqdorni o'rnatadi (0 — o'chirish); haqiqiy saqlangan miqdorni qaytaradi."""
    item = await _get_item(session, user_id, product_id)
    if quantity <= 0:
        if item:
            await session.delete(item)
            await session.commit()
        return 0
    if not _orderable(await session.get(Product, product_id)):
        raise ProductUnavailable
    quantity = min(quantity, MAX_QTY)
    if item is None:
        session.add(CartItem(user_id=user_id, product_id=product_id, quantity=quantity))
    else:
        item.quantity = quantity
    await session.commit()
    return quantity


async def add_item(session: AsyncSession, user_id: int, product_id: int, quantity: int = 1) -> int:
    item = await _get_item(session, user_id, product_id)
    current = item.quantity if item else 0
    return await set_quantity(session, user_id, product_id, current + max(1, quantity))


async def clear_cart(session: AsyncSession, user_id: int) -> None:
    await session.execute(delete(CartItem).where(CartItem.user_id == user_id))
    await session.commit()
