from savatcha.core.config import Settings
from savatcha.core.i18n import t
from savatcha.core.repo import users


def test_settings_parse_csv(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite://")
    monkeypatch.setenv("ADMIN_IDS", "1, 2,3")
    s = Settings(_env_file=None)
    assert s.admin_ids == [1, 2, 3]
    assert s.stats_revenue_statuses == ["accepted", "delivering", "done"]


def test_i18n_fallback():
    assert t("menu_cart", "ru") == "🛒 Корзина"
    assert t("menu_cart", None) == "🛒 Savat"
    assert t("no_such_key", "ru") == "no_such_key"


async def test_user_get_or_create_and_lang(session):
    u = await users.get_or_create(session, 42, "Ali Valiyev", "ali")
    assert u.lang is None
    await users.set_lang(session, u, "ru")
    again = await users.get_or_create(session, 42, "Ali V.", "ali")
    assert again.id == u.id and again.lang == "ru" and again.full_name == "Ali V."
