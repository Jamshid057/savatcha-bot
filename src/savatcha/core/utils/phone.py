import re

_PHONE_RE = re.compile(r"^\+998\d{9}$")


def normalize_phone(raw: str) -> str | None:
    """`+998XXXXXXXXX` ko'rinishiga keltiradi; yaroqsiz bo'lsa None."""
    cleaned = re.sub(r"[\s\-()]", "", raw.strip())
    if cleaned.startswith("998") and cleaned.isdigit():
        cleaned = "+" + cleaned
    elif len(cleaned) == 9 and cleaned.isdigit():
        cleaned = "+998" + cleaned
    return cleaned if _PHONE_RE.match(cleaned) else None
