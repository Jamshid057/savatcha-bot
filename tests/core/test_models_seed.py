from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from savatcha.core.db.models import CartItem, Category, Product, User
from savatcha.core.seed import seed


async def test_seed_creates_demo_data_and_is_idempotent(session, tmp_path):
    assert await seed(session, str(tmp_path)) is True
    assert await seed(session, str(tmp_path)) is False

    cats = await session.scalar(select(func.count()).select_from(Category))
    prods = await session.scalar(select(func.count()).select_from(Product))
    assert cats == 5
    assert 15 <= prods <= 20
    images = list((tmp_path / "products").glob("*.jpg"))
    assert len(images) == prods
    price = await session.scalar(select(Product.price).limit(1))
    assert isinstance(price, Decimal)


async def test_cart_item_unique_per_user_product(session):
    user = User(tg_id=1, full_name="A")
    cat = Category(name_uz="k", name_ru="к")
    session.add_all([user, cat])
    await session.flush()
    prod = Product(category_id=cat.id, name_uz="p", name_ru="п", price=Decimal("1000"))
    session.add(prod)
    await session.flush()
    session.add(CartItem(user_id=user.id, product_id=prod.id, quantity=1))
    await session.flush()
    session.add(CartItem(user_id=user.id, product_id=prod.id, quantity=2))
    with pytest.raises(IntegrityError):
        await session.flush()
