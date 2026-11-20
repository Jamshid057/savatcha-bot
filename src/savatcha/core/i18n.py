import json
from functools import lru_cache
from pathlib import Path

LOCALES_DIR = Path(__file__).parent / "locales"
SUPPORTED = ("uz", "ru")
DEFAULT = "uz"


@lru_cache
def _load(lang: str) -> dict[str, str]:
    return json.loads((LOCALES_DIR / f"{lang}.json").read_text(encoding="utf-8"))


def t(key: str, lang: str | None = None, **kwargs: object) -> str:
    lang = lang if lang in SUPPORTED else DEFAULT
    text = _load(lang).get(key) or _load(DEFAULT).get(key) or key
    return text.format(**kwargs) if kwargs else text
