import time

import pytest

from savatcha.api.auth import InitDataError, validate_init_data
from tests.api.conftest import ADMIN, CLIENT, TOKEN_APP, make_init_data, tma


def test_validate_ok():
    user = validate_init_data(make_init_data(CLIENT, first_name="Vali"), TOKEN_APP, 86400)
    assert user.id == CLIENT and user.full_name == "Vali" and user.username == f"u{CLIENT}"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"tamper": True},  # imzo mos kelmaydi
        {"token": "999:OTHER"},  # boshqa bot imzosi
        {"auth_date": int(time.time()) - 90000},  # eskirgan
    ],
)
def test_validate_rejects(kwargs):
    with pytest.raises(InitDataError):
        validate_init_data(make_init_data(CLIENT, **kwargs), TOKEN_APP, 86400)


@pytest.mark.parametrize("raw", ["", "user=%7B%7D", "auth_date=1&hash=abc"])
def test_validate_rejects_garbage(raw):
    with pytest.raises(InitDataError):
        validate_init_data(raw, TOKEN_APP, 86400)


async def test_health_is_public_and_docs_closed(env):
    assert (await env.client.get("/api/health")).json() == {"status": "ok"}
    assert (await env.client.get("/docs")).status_code == 404


async def test_endpoints_require_valid_init_data(env):
    c = env.client
    assert (await c.get("/api/me")).status_code == 401
    assert (await c.get("/api/categories")).status_code == 401
    assert (await c.get("/api/me", headers={"Authorization": "Bearer x"})).status_code == 401
    assert (await c.get("/api/me", headers=tma(CLIENT, tamper=True))).status_code == 401
    assert (await c.get("/api/me", headers=tma(CLIENT, auth_date=1))).status_code == 401


async def test_me_creates_user_and_detects_admin(env):
    me = (await env.client.get("/api/me", headers=tma(CLIENT, lang="ru"))).json()
    assert me["tg_id"] == CLIENT and me["is_admin"] is False and me["lang"] == "ru"
    assert (await env.client.get("/api/me", headers=tma(ADMIN))).json()["is_admin"] is True


async def test_patch_me(env):
    h = tma(CLIENT)
    r = await env.client.patch("/api/me", json={"lang": "ru", "phone": "90 123 45 67"}, headers=h)
    assert r.json()["lang"] == "ru" and r.json()["phone"] == "+998901234567"
    assert (await env.client.patch("/api/me", json={"phone": "12"}, headers=h)).status_code == 422
    assert (await env.client.patch("/api/me", json={"lang": "en"}, headers=h)).status_code == 422


async def test_admin_endpoints_forbidden_for_regular_user(env):
    h = tma(CLIENT)
    for method, path in [
        ("GET", "/api/admin/orders"),
        ("GET", "/api/admin/products"),
        ("GET", "/api/admin/categories"),
        ("DELETE", "/api/admin/categories/1"),
        ("PATCH", "/api/admin/orders/1/status"),
        ("GET", "/api/admin/orders/1/receipt"),
    ]:
        r = await env.client.request(method, path, headers=h, json={"status": "accepted"})
        assert r.status_code == 403, (method, path)
    assert (await env.client.get("/api/admin/orders")).status_code == 401
