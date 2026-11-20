import json
import re
from pathlib import Path

from savatcha.core.i18n import LOCALES_DIR

SRC = Path(__file__).parent.parent / "src"


def _load(lang: str) -> dict[str, str]:
    return json.loads((LOCALES_DIR / f"{lang}.json").read_text(encoding="utf-8"))


def test_uz_ru_have_same_keys_and_placeholders():
    uz, ru = _load("uz"), _load("ru")
    assert set(uz) == set(ru)
    for key in uz:
        assert set(re.findall(r"{(\w+)}", uz[key])) == set(re.findall(r"{(\w+)}", ru[key])), key


def test_every_key_used_in_code_exists():
    uz = _load("uz")
    used: set[str] = set()
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        used |= set(re.findall(r"\bt\(\s*\"([a-z][a-z_0-9]*)\"", text))
        # t("a" if x else "b", ...) ko'rinishidagi shartli kalitlar
        for m in re.finditer(r"\bt\(\s*\"([a-z_0-9]+)\" if [^\"]+ else \"([a-z_0-9]+)\"", text):
            used |= set(m.groups())
    used -= {"q", "image", "price", "comment", "receipt", "user_id", "event_from_user"}
    used -= {k for k in used if k.startswith(("name_", "description_"))}
    assert used - set(uz) == set()


def test_dynamic_keys_exist():
    uz = _load("uz")
    from savatcha.core.db.models import ORDER_STATUSES
    from savatcha.core.services.orders import STATUS_GROUPS

    for s in ORDER_STATUSES:
        assert f"status_{s}" in uz
    for g in STATUS_GROUPS:
        assert f"grp_{g}" in uz
    for c in ("too_large", "invalid", "type"):
        assert f"image_err_{c}" in uz
    for f in ("name_uz", "name_ru", "description_uz", "description_ru", "price", "image"):
        assert f"ask_edit_{f}" in uz
