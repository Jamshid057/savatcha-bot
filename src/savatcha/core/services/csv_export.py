import csv
import io
from collections.abc import Iterable, Sequence

from savatcha.core.db.models import Order
from savatcha.core.services.customers import CustomerRow

_DANGEROUS = ("=", "+", "-", "@", "\t", "\r")


def safe_cell(value: object) -> str:
    """CSV/Excel formula injection dan himoya: xavfli boshlanishga `'` qo'yiladi."""
    text = "" if value is None else str(value)
    return f"'{text}" if text.startswith(_DANGEROUS) else text


def _write(header: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    for row in rows:
        writer.writerow([safe_cell(c) for c in row])
    return "﻿" + buf.getvalue()  # BOM: Excel UTF-8 ni to'g'ri ochadi


def orders_csv(orders: Iterable[Order]) -> str:
    return _write(
        ["id", "created_at", "source", "status", "customer", "phone", "address", "total", "items"],
        (
            [
                o.id,
                o.created_at.isoformat(timespec="seconds"),
                o.source,
                o.status,
                o.customer_name,
                o.phone,
                o.address,
                o.total,
                "; ".join(f"{i.name_snapshot} x{i.quantity}" for i in o.items),
            ]
            for o in orders
        ),
    )


def customers_csv(rows: Iterable[CustomerRow]) -> str:
    return _write(
        ["id", "name", "username", "phone", "lang", "orders", "total_spent", "last_order_at"],
        (
            [
                r.user.id,
                r.user.full_name,
                r.user.username or "",
                r.user.phone or "",
                r.user.lang or "",
                r.orders_count,
                r.total_spent,
                r.last_order_at.isoformat(timespec="seconds") if r.last_order_at else "",
            ]
            for r in rows
        ),
    )
