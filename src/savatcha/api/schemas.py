from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from savatcha.core.db.models import Order, Product, User
from savatcha.core.services.cart import Cart


class UserOut(BaseModel):
    id: int
    tg_id: int
    full_name: str
    username: str | None
    lang: str | None
    phone: str | None
    is_admin: bool


def user_out(user: User, admin_ids: list[int]) -> UserOut:
    return UserOut(
        id=user.id,
        tg_id=user.tg_id,
        full_name=user.full_name,
        username=user.username,
        lang=user.lang,
        phone=user.phone,
        is_admin=user.tg_id in admin_ids,
    )


class UserPatch(BaseModel):
    lang: Literal["uz", "ru"] | None = None
    phone: str | None = None


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name_uz: str
    name_ru: str
    sort_order: int
    is_active: bool


class CategoryIn(BaseModel):
    name_uz: str = Field(min_length=1, max_length=100)
    name_ru: str = Field(min_length=1, max_length=100)
    is_active: bool = True


class CategoryPatch(BaseModel):
    name_uz: str | None = Field(default=None, min_length=1, max_length=100)
    name_ru: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None


class ProductOut(BaseModel):
    id: int
    category_id: int
    name_uz: str
    name_ru: str
    description_uz: str
    description_ru: str
    price: Decimal
    image_url: str | None
    is_available: bool
    is_archived: bool


def product_out(p: Product) -> ProductOut:
    image_url = f"/files/{p.image_path.removeprefix('products/')}" if p.image_path else None
    return ProductOut(
        id=p.id,
        category_id=p.category_id,
        name_uz=p.name_uz,
        name_ru=p.name_ru,
        description_uz=p.description_uz,
        description_ru=p.description_ru,
        price=p.price,
        image_url=image_url,
        is_available=p.is_available,
        is_archived=p.is_archived,
    )


class ProductPage(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    pages: int


class CartLineOut(BaseModel):
    product: ProductOut
    quantity: int
    subtotal: Decimal


class CartOut(BaseModel):
    lines: list[CartLineOut]
    total: Decimal
    removed: list[ProductOut]


def cart_out(cart: Cart) -> CartOut:
    return CartOut(
        lines=[
            CartLineOut(product=product_out(ln.product), quantity=ln.quantity, subtotal=ln.subtotal)
            for ln in cart.lines
        ],
        total=cart.total,
        removed=[product_out(p) for p in cart.removed],
    )


class QuantityIn(BaseModel):
    quantity: int = Field(ge=0, le=999)


class OrderItemOut(BaseModel):
    product_id: int
    name: str
    price: Decimal
    quantity: int
    subtotal: Decimal


class HistoryOut(BaseModel):
    from_status: str | None
    to_status: str
    changed_by_tg_id: int | None
    created_at: datetime


class OrderOut(BaseModel):
    id: int
    source: str
    status: str
    customer_name: str
    phone: str
    address: str
    comment: str | None
    has_receipt: bool
    total: Decimal
    created_at: datetime
    items: list[OrderItemOut]
    history: list[HistoryOut]


def order_out(o: Order) -> OrderOut:
    return OrderOut(
        id=o.id,
        source=o.source,
        status=o.status,
        customer_name=o.customer_name,
        phone=o.phone,
        address=o.address,
        comment=o.comment,
        has_receipt=bool(o.receipt_path),
        total=o.total,
        created_at=o.created_at,
        items=[
            OrderItemOut(
                product_id=i.product_id,
                name=i.name_snapshot,
                price=i.price_snapshot,
                quantity=i.quantity,
                subtotal=i.price_snapshot * i.quantity,
            )
            for i in o.items
        ],
        history=[
            HistoryOut(
                from_status=h.from_status,
                to_status=h.to_status,
                changed_by_tg_id=h.changed_by_tg_id,
                created_at=h.created_at,
            )
            for h in o.history
        ],
    )


class OrderPage(BaseModel):
    items: list[OrderOut]
    total: int
    page: int
    pages: int


class StatusIn(BaseModel):
    status: str
