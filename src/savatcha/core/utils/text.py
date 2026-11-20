TG_LIMIT = 4000


def split_text(text: str, limit: int = TG_LIMIT) -> list[str]:
    """Uzun matnni qator chegarasida Telegram limitiga mos bo'laklarga bo'ladi."""
    parts: list[str] = []
    current = ""
    for line in text.split("\n"):
        while len(line) > limit:
            if current:
                parts.append(current)
                current = ""
            parts.append(line[:limit])
            line = line[limit:]
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            parts.append(current)
            current = line
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts or [""]
