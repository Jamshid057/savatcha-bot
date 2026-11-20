import re
from decimal import Decimal, InvalidOperation

MAX_PRICE = Decimal("1000000000")


def format_price(amount: Decimal | int, lang: str | None = None) -> str:
    unit = "сум" if lang == "ru" else "so'm"
    return f"{int(Decimal(amount)):,}".replace(",", " ") + f" {unit}"


def parse_price(raw: str) -> Decimal | None:
    """'12 000', '12000.50' -> Decimal; noto'g'ri yoki <= 0 bo'lsa None."""
    cleaned = re.sub(r"\s", "", raw).replace(",", ".")
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    if not value.is_finite() or value <= 0 or value > MAX_PRICE:
        return None
    return value.quantize(Decimal("0.01"))
