import io
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from PIL import Image

from savatcha.core.db.models import Category, Order, User
from savatcha.core.services import cart, catalog, files, orders, stats
from savatcha.core.utils.money import format_price, parse_price
from savatcha.core.utils.phone import normalize_phone
from savatcha.core.utils.text import split_text


# ---- utils ----
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("+998901234567", "+998901234567"),
        ("998901234567", "+998901234567"),
        ("90 123-45-67", "+998901234567"),
        ("+99890123456", None),
        ("+79001234567", None),
        ("abc", None),
    ],
)
def test_normalize_phone(raw, expected):
    assert normalize_phone(raw) == expected


def test_money():
    assert format_price(Decimal("12000")) == "12 000 so'm"
    assert format_price(95000, "ru") == "95 000 сум"
    assert parse_price("12 000") == Decimal("12000.00")
    assert parse_price("12000,5") == Decimal("12000.50")
    for bad in ("0", "-5", "abc", "nan", "1e20", ""):
        assert parse_price(bad) is None


def test_split_text():
    text = "\n".join(["x" * 30] * 10)
    parts = split_text(text, limit=100)
    assert all(len(p) <= 100 for p in parts)
    assert "\n".join(parts) == text
    assert len(split_text("y" * 250, limit=100)) == 3


# ---- fayllar ----
def _img(fmt: str, size=(40, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (200, 10, 10)).save(buf, fmt)
    return buf.getvalue()


async def test_save_image_ok_and_rejects(tmp_path):
    rel = await files.save_image(_img("PNG"), str(tmp_path), "receipts")
    assert rel.startswith("receipts/") and rel.endswith(".png")
    assert files.resolve_path(str(tmp_path), rel) is not None
    with pytest.raises(files.ImageError) as e:
        await files.save_image(b"not an image", str(tmp_path), "receipts")
    assert e.value.code == "invalid"
    with pytest.raises(files.ImageError) as e:
        await files.save_image(_img("GIF"), str(tmp_path), "receipts")
    assert e.value.code == "type"
    with pytest.raises(files.ImageError) as e:
        await files.save_image(_img("PNG"), str(tmp_path), "receipts", max_mb=0)
    assert e.value.code == "too_large"


def test_resolve_path_blocks_traversal(tmp_path):
    (tmp_path / "products").mkdir()
    (tmp_path / "products" / "a.jpg").write_bytes(b"x")
    outside = tmp_path.parent / "secret.txt"
    outside.write_text("s")
    assert files.resolve_path(str(tmp_path), "products/a.jpg") is not None
    assert files.resolve_path(str(tmp_path), "../secret.txt") is None


# ---- katalog ----
async def _shop(session):
    cat = await catalog.create_category(session, "Ichimlik", "Напитки")
    cheap = await catalog.create_product(
        session, category_id=cat.id, name_uz="Cola", name_ru="Кола", description_uz="",
        description_ru="", price=Decimal("10000"), image_path=None,
    )  # fmt: skip
    pricey = await catalog.create_product(
        session, category_id=cat.id, name_uz="Sharbat 100%", name_ru="Сок", description_uz="",
        description_ru="", price=Decimal("25000.50"), image_path=None,
    )  # fmt: skip
    return cat, cheap, pricey


async def test_catalog_search_pagination_and_archive(session):
    cat, cheap, pricey = await _shop(session)
    items, total = await catalog.list_products(session, category_id=cat.id, per_page=1, page=2)
    assert total == 2 and len(items) == 1
    found, _ = await catalog.list_products(session, query="COLA")
    assert [p.id for p in found] == [cheap.id]
    found, _ = await catalog.list_products(session, query="100%")  # % maxsus belgi emas
    assert [p.id for p in found] == [pricey.id]
    assert (await catalog.list_products(session, query="%"))[1] == 1
    await catalog.archive_product(session, cheap)
    assert (await catalog.list_products(session, category_id=cat.id))[1] == 1


async def test_category_delete_rules_and_inactive_hidden(session):
    cat, product, _ = await _shop(session)
    with pytest.raises(catalog.CategoryNotEmpty):
        await catalog.delete_category(session, cat)
    await catalog.archive_product(session, product)
    with pytest.raises(catalog.CategoryNotEmpty):  # arxivlangani ham sanaladi
        await catalog.delete_category(session, cat)
    await catalog.set_category_active(session, cat, False)
    assert (await catalog.list_products(session))[1] == 0
    assert (await catalog.list_products(session, storefront=False))[1] == 1
    empty = await catalog.create_category(session, "Bo'sh", "Пусто")
    await catalog.delete_category(session, empty)


async def test_update_product_whitelist_and_price(session):
    _, p, _ = await _shop(session)
    with pytest.raises(catalog.CatalogError):
        await catalog.update_product(session, p, id=5)
    with pytest.raises(catalog.CatalogError):
        await catalog.update_product(session, p, price=Decimal("-1"))
    p.tg_file_id = "abc"
    await catalog.update_product(session, p, image_path="products/x.jpg")
    assert p.tg_file_id is None


# ---- savat ----
async def test_cart_totals_limits_and_isolation(session):
    _, cheap, pricey = await _shop(session)
    a, b = User(tg_id=1, full_name="A"), User(tg_id=2, full_name="B")
    session.add_all([a, b])
    await session.commit()
    await cart.add_item(session, a.id, cheap.id, 2)
    await cart.add_item(session, a.id, cheap.id)
    await cart.add_item(session, a.id, pricey.id)
    c = await cart.get_cart(session, a.id)
    assert [ln.quantity for ln in c.lines] == [3, 1]
    assert c.total == Decimal("55000.50")
    assert (await cart.get_cart(session, b.id)).lines == []
    assert await cart.set_quantity(session, a.id, cheap.id, 500) == cart.MAX_QTY
    assert await cart.set_quantity(session, a.id, cheap.id, 0) == 0
    assert len((await cart.get_cart(session, a.id)).lines) == 1


async def test_cart_drops_unavailable_products(session):
    _, cheap, pricey = await _shop(session)
    u = User(tg_id=1, full_name="A")
    session.add(u)
    await session.commit()
    await cart.add_item(session, u.id, cheap.id)
    await cart.add_item(session, u.id, pricey.id)
    await catalog.toggle_available(session, cheap)
    c = await cart.get_cart(session, u.id)
    assert [ln.product.id for ln in c.lines] == [pricey.id]
    assert [p.id for p in c.removed] == [cheap.id]
    with pytest.raises(cart.ProductUnavailable):
        await cart.add_item(session, u.id, cheap.id)


# ---- buyurtma ----
async def _user_with_cart(session):
    _, cheap, pricey = await _shop(session)
    u = User(tg_id=7, full_name="Ali")
    session.add(u)
    await session.commit()
    await cart.add_item(session, u.id, cheap.id, 2)
    await cart.add_item(session, u.id, pricey.id)
    return u, cheap, pricey


async def test_create_order_snapshots_and_clears_cart(session):
    u, cheap, _ = await _user_with_cart(session)
    order = await orders.create_order(
        session, u, source="classic", customer_name=" Ali ", phone="90 123 45 67",
        address="Toshkent, Chilonzor", comment="  ", receipt_path=None,
    )  # fmt: skip
    assert order.total == Decimal("45000.50") and order.phone == "+998901234567"
    assert order.comment is None and order.customer_name == "Ali"
    # narx o'zgarsa ham buyurtma o'zgarmaydi
    await catalog.update_product(session, cheap, price=Decimal("99999"), name_uz="Yangi")
    full = await orders.get_order(session, order.id)
    snap = {i.name_snapshot: i.price_snapshot for i in full.items}
    assert snap["Cola"] == Decimal("10000.00")
    assert [(h.from_status, h.to_status) for h in full.history] == [(None, "new")]
    assert (await cart.get_cart(session, u.id)).lines == []
    with pytest.raises(orders.EmptyCartError):
        await orders.create_order(
            session, u, source="classic", customer_name="A", phone="901234567",
            address="addr12", comment=None, receipt_path=None,
        )  # fmt: skip


async def test_create_order_validation(session):
    u, *_ = await _user_with_cart(session)
    with pytest.raises(orders.InvalidPhone):
        await orders.create_order(
            session, u, source="classic", customer_name="A", phone="123",
            address="addr12", comment=None, receipt_path=None,
        )  # fmt: skip
    with pytest.raises(orders.OrderError):
        await orders.create_order(
            session, u, source="web", customer_name="A", phone="901234567",
            address="addr12", comment=None, receipt_path=None,
        )  # fmt: skip
    assert len((await cart.get_cart(session, u.id)).lines) == 2  # xatoda savat saqlanadi


async def test_status_transitions_and_history(session):
    u, *_ = await _user_with_cart(session)
    o = await orders.create_order(
        session, u, source="classic", customer_name="A", phone="901234567",
        address="addr12", comment=None, receipt_path=None,
    )  # fmt: skip
    with pytest.raises(orders.InvalidTransition):
        await orders.change_status(session, o, "done", 1)
    for s in ("accepted", "delivering", "done"):
        await orders.change_status(session, o, s, 111)
    with pytest.raises(orders.InvalidTransition):
        await orders.change_status(session, o, "cancelled", 111)
    full = await orders.get_order(session, o.id)
    assert [h.to_status for h in full.history] == ["new", "accepted", "delivering", "done"]
    assert full.history[1].changed_by_tg_id == 111
    assert await orders.get_order(session, o.id, user_id=u.id + 1) is None
    listed, total = await orders.list_orders(session, group="done")
    assert total == 1 and listed[0].id == o.id
    assert (await orders.list_orders(session, group="new"))[1] == 0


# ---- statistika ----
async def test_stats_tashkent_day_boundary_and_revenue_statuses(session):
    cat = Category(name_uz="k", name_ru="к")
    u = User(tg_id=1, full_name="A")
    session.add_all([u, cat])
    await session.flush()

    def mk(created, status, total):
        return Order(
            user_id=u.id, source="classic", status=status, customer_name="A", phone="+998901234567",
            address="x", total=Decimal(total), created_at=created,
        )  # fmt: skip

    session.add_all(
        [
            # 2026-11-20 Toshkent kuni: 19:00 UTC (00:00 UZT 21-nov dan oldin) -> 20-noyabr 24:00
            mk(datetime(2026, 11, 20, 18, 59, tzinfo=UTC), "done", "100"),  # 20-nov 23:59 UZT
            mk(datetime(2026, 11, 20, 19, 0, tzinfo=UTC), "done", "200"),  # 21-nov 00:00 UZT
            mk(datetime(2026, 11, 21, 10, 0, tzinfo=UTC), "accepted", "300"),
            mk(datetime(2026, 11, 21, 11, 0, tzinfo=UTC), "cancelled", "999"),
            mk(datetime(2026, 11, 21, 12, 0, tzinfo=UTC), "new", "888"),
        ]
    )
    await session.commit()
    data = await stats.today_and_week(
        session, ["accepted", "delivering", "done"], today=date(2026, 11, 21)
    )
    assert data["today"] == (2, Decimal("500"))
    assert data["week"] == (3, Decimal("600"))
