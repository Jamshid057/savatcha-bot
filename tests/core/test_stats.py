"""Statistika: aniq ma'lumot to'plami -> kutilgan summalar (Toshkent = UTC+5)."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from savatcha.core.db.models import Category, Order, OrderItem, Product, User
from savatcha.core.services import stats

REV = ["accepted", "delivering", "done"]
D_FROM, D_TO = date(2026, 11, 10), date(2026, 11, 12)


def utc(day: int, hh: int, mm: int = 0) -> datetime:
    return datetime(2026, 11, day, hh, mm, tzinfo=UTC)


@pytest.fixture
async def data(session):
    c1, c2 = Category(name_uz="K1", name_ru="К1"), Category(name_uz="K2", name_ru="К2")
    session.add_all([c1, c2])
    await session.flush()

    def prod(cat, name, price, archived=False):
        return Product(
            category_id=cat.id,
            name_uz=name,
            name_ru=name,
            price=Decimal(price),
            is_archived=archived,
        )

    p1, p2, p3 = prod(c1, "P1", 100), prod(c1, "P2", 50), prod(c2, "P3", 300)
    p4, p5 = prod(c2, "P4-never-sold", 10), prod(c2, "P5-archived", 10, archived=True)
    session.add_all([p1, p2, p3, p4, p5])
    # created_at: u1 10-nov, u2 12-nov (Toshkent), u3 8-nov (oldingi davr), u4 davrdan tashqarida
    u1, u2, u3, u4 = (
        User(tg_id=i, full_name=f"U{i}", created_at=at)
        for i, at in ((1, utc(10, 5)), (2, utc(12, 6)), (3, utc(8, 6)), (4, utc(1, 6)))
    )
    session.add_all([u1, u2, u3, u4])
    await session.flush()

    def order(user, source, status, created, items):
        total = sum(Decimal(pr.price) * qty for pr, qty in items)
        o = Order(
            user_id=user.id, source=source, status=status, customer_name="x", phone="+998900000000",
            address="addr", total=total, created_at=created,
            items=[
                OrderItem(product_id=pr.id, name_snapshot=pr.name_uz, price_snapshot=pr.price, quantity=q)
                for pr, q in items
            ],
        )  # fmt: skip
        session.add(o)

    order(u1, "classic", "done", utc(9, 19, 30), [(p1, 1)])  # 10-nov 00:30 UZT
    order(u1, "miniapp", "accepted", utc(10, 7), [(p1, 2), (p2, 1)])  # 10-nov 12:00 UZT
    order(u2, "miniapp", "cancelled", utc(11, 10), [(p1, 5)])  # bekor: tushumga kirmaydi
    order(u2, "classic", "delivering", utc(12, 18, 59), [(p3, 1)])  # 12-nov 23:59 UZT
    order(u3, "classic", "done", utc(12, 19, 0), [(p1, 1)])  # 13-nov 00:00 UZT: davrdan tashqari
    order(u3, "classic", "done", utc(9, 18, 59), [(p2, 2)])  # 9-nov 23:59 UZT: oldingi davr
    order(u4, "miniapp", "new", utc(11, 9), [(p2, 1)])  # yangi: tushumga kirmaydi
    await session.commit()
    return {"p": (p1, p2, p3, p4, p5), "c": (c1, c2)}


async def test_summary_kpis_and_previous_period_comparison(session, data):
    s = await stats.summary(session, D_FROM, D_TO, REV)
    assert s["current"] == {
        "orders": 3,
        "revenue": Decimal("650"),
        "avg_check": Decimal("216.67"),
        "new_customers": 2,
    }
    assert s["previous"]["orders"] == 1 and s["previous"]["revenue"] == Decimal("100")
    assert s["previous"]["new_customers"] == 1
    assert s["change"]["orders"] == 200.0 and s["change"]["revenue"] == 550.0
    assert s["change"]["new_customers"] == 100.0
    assert s["pending"] == 1
    assert s["period"]["prev_from"] == date(2026, 11, 7) and s["period"]["prev_to"] == date(
        2026, 11, 9
    )


async def test_change_is_none_when_previous_is_zero(session, data):
    s = await stats.summary(session, date(2026, 11, 1), date(2026, 11, 3), REV)
    assert s["current"]["orders"] == 0 and s["change"]["orders"] == 0.0  # 0 -> 0
    s = await stats.summary(session, date(2026, 11, 7), date(2026, 11, 9), REV)
    assert s["current"]["orders"] == 1 and s["change"]["orders"] is None  # 0 dan o'sish


async def test_sales_by_day_uses_tashkent_days_and_fills_gaps(session, data):
    rows = await stats.sales_by_day(session, D_FROM, D_TO, REV)
    assert [(r["date"], r["orders"], r["revenue"]) for r in rows] == [
        (date(2026, 11, 10), 2, Decimal("350")),  # 00:30 va 12:00 UZT, ikkisi 10-noyabr
        (date(2026, 11, 11), 0, Decimal("0")),  # bekor qilingan hisobga olinmaydi
        (date(2026, 11, 12), 1, Decimal("300")),  # 23:59 UZT hali 12-noyabr
    ]
    wide = await stats.sales_by_day(session, date(2026, 11, 9), date(2026, 11, 13), REV)
    assert len(wide) == 5
    assert wide[0]["revenue"] == Decimal("100") and wide[4]["revenue"] == Decimal("100")


async def test_orders_by_status_includes_every_status(session, data):
    rows = await stats.orders_by_status(session, D_FROM, D_TO)
    assert {r["status"]: r["orders"] for r in rows} == {
        "new": 1,
        "accepted": 1,
        "delivering": 1,
        "done": 1,
        "cancelled": 1,
    }


async def test_by_source_category_and_hour(session, data):
    src = {
        r["source"]: (r["orders"], r["revenue"])
        for r in await stats.by_source(session, D_FROM, D_TO, REV)
    }
    assert src == {"classic": (2, Decimal("400")), "miniapp": (1, Decimal("250"))}
    cats = await stats.by_category(session, D_FROM, D_TO, REV)
    assert [(c["name_uz"], c["revenue"]) for c in cats] == [
        ("K1", Decimal("350")),
        ("K2", Decimal("300")),
    ]
    hours = await stats.by_hour(session, D_FROM, D_TO, REV)
    assert len(hours) == 24
    assert {h["hour"]: h["orders"] for h in hours if h["orders"]} == {0: 1, 12: 1, 23: 1}


async def test_top_products_order_and_cancelled_excluded(session, data):
    by_qty = await stats.top_products(session, REV, by="qty", d_from=D_FROM, d_to=D_TO)
    assert [(p["name_uz"], p["quantity"]) for p in by_qty] == [("P1", 3), ("P2", 1), ("P3", 1)]
    by_rev = await stats.top_products(session, REV, by="revenue", d_from=D_FROM, d_to=D_TO)
    assert [(p["name_uz"], p["revenue"]) for p in by_rev] == [
        ("P1", Decimal("300")),
        ("P3", Decimal("300")),  # teng bo'lsa id bo'yicha
        ("P2", Decimal("50")),
    ]
    all_time = await stats.top_products(session, REV, by="qty", limit=2)
    assert [(p["name_uz"], p["quantity"]) for p in all_time] == [("P1", 4), ("P2", 3)]


async def test_slow_products_excludes_sold_and_archived(session, data):
    slow = await stats.slow_products(session, REV, days=30, now=utc(13, 0))
    assert [p["name_uz"] for p in slow] == ["P4-never-sold"]
    # 1 kunlik oyna: faqat 12-noyabrdan keyin sotilganlar "sotilgan"
    slow = await stats.slow_products(session, REV, days=1, now=utc(13, 0))
    assert [p["name_uz"] for p in slow] == ["P2", "P4-never-sold"]


async def test_product_detail_series(session, data):
    p1 = data["p"][0]
    d = await stats.product_detail(session, p1.id, D_FROM, D_TO, REV)
    assert [(x["date"], x["quantity"], x["revenue"]) for x in d["series"]] == [
        (date(2026, 11, 10), 3, Decimal("300")),
        (date(2026, 11, 11), 0, Decimal("0")),
        (date(2026, 11, 12), 0, Decimal("0")),
    ]
    assert d["total_quantity"] == 3 and d["total_revenue"] == Decimal("300")


async def test_top_customers_and_repeat_share(session, data):
    r = await stats.top_customers(session, REV, limit=2)
    assert [(c["full_name"], c["orders"], c["total_spent"]) for c in r["customers"]] == [
        ("U1", 2, Decimal("350")),
        ("U2", 1, Decimal("300")),
    ]
    assert r["buyers"] == 3 and r["repeat_buyers"] == 2 and r["repeat_share"] == 66.7


async def test_new_customers_by_day(session, data):
    rows = await stats.new_customers_by_day(session, D_FROM, D_TO)
    assert [(r["date"], r["customers"]) for r in rows] == [
        (date(2026, 11, 10), 1),
        (date(2026, 11, 11), 0),
        (date(2026, 11, 12), 1),
    ]
