from datetime import date, timedelta

from fastapi import HTTPException, Query

from savatcha.core.services.stats import today_tashkent

MAX_RANGE_DAYS = 366


def parse_period(
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = Query(default=None),
) -> tuple[date, date]:
    """Standart: oxirgi 7 kun (bugun bilan), Toshkent vaqti."""
    end = to or today_tashkent()
    start = from_ or end - timedelta(days=6)
    if start > end or (end - start).days >= MAX_RANGE_DAYS:
        raise HTTPException(422, "invalid_range")
    return start, end
