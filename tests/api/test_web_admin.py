import hashlib
import hmac
import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from savatcha.core.db.models import AdminSession, AuditLog
from savatcha.core.services.stats import today_tashkent
from tests.api.conftest import ADMIN, CLIENT, OTHER, TOKEN_APP, png_bytes, tma

ORIGIN = {"Origin": "https://shop.example.com"}


def widget_data(
    user_id: int,
    *,
    token: str = TOKEN_APP,
    auth_date: int | None = None,
    tamper: bool = False,
) -> dict[str, str]:
    data = {
        "id": str(user_id),
        "first_name": "Admin",
        "username": "boss",
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
    }
    check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret = hashlib.sha256(token.encode()).digest()
    data["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if tamper:
        data["first_name"] = "Hacker"
    return data


def token_of(response) -> str:
    """Secure cookie http test klientida saqlanmaydi, shuning uchun sarlavhadan olamiz."""
    return response.headers["set-cookie"].split("savatcha_session=")[1].split(";")[0]


async def login(env, user_id=ADMIN, **kw):
    return await env.client.post(
        "/api/auth/telegram-login", json=widget_data(user_id, **kw), headers=ORIGIN
    )


async def test_login_rejects_bad_signature_expired_and_non_admin(env):
    assert (await login(env, tamper=True)).status_code == 401
    assert (await login(env, token="999:OTHER")).status_code == 401
    assert (await login(env, auth_date=int(time.time()) - 301)).status_code == 401
    assert (await login(env, user_id=CLIENT)).status_code == 403  # imzo to'g'ri, lekin admin emas
    r = await env.client.post("/api/auth/telegram-login", json={"id": "1"}, headers=ORIGIN)
    assert r.status_code == 401


async def test_login_sets_secure_cookie_and_session_works(env):
    r = await login(env)
    assert r.status_code == 200 and r.json()["tg_id"] == ADMIN
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "secure" in cookie and "samesite=strict" in cookie
    assert f"max-age={12 * 3600}" in cookie
    # cookie bilan admin endpointlar ochiladi, tma siz
    env.client.cookies.set("savatcha_session", token_of(r))
    assert (await env.client.get("/api/admin/orders")).status_code == 200
    assert (await env.client.get("/api/me")).json()["is_admin"] is True
    state = (await env.client.get("/api/auth/session")).json()
    assert state["authenticated"] is True and state["tg_id"] == ADMIN
    # token DB da faqat hash ko'rinishida
    async with env.sf() as s:
        row = await s.scalar(select(AdminSession))
    assert row.token_hash == hashlib.sha256(token_of(r).encode()).hexdigest()
    assert token_of(r) not in row.token_hash


async def test_csrf_blocks_cookie_mutations_without_allowed_origin(env):
    r = await login(env)
    env.client.cookies.set("savatcha_session", token_of(r))
    body = {"name_uz": "A", "name_ru": "Б"}
    assert (await env.client.post("/api/admin/categories", json=body)).status_code == 403
    evil = {"Origin": "https://evil.example.com"}
    assert (
        await env.client.post("/api/admin/categories", json=body, headers=evil)
    ).status_code == 403
    assert (
        await env.client.post("/api/admin/categories", json=body, headers=ORIGIN)
    ).status_code == 201
    ref = {"Referer": "https://shop.example.com/admin/categories"}
    assert (
        await env.client.post("/api/admin/categories", json=body, headers=ref)
    ).status_code == 201
    # GET uchun Origin shart emas; tma sarlavhasi CSRF ga bog'liq emas
    assert (await env.client.get("/api/admin/categories")).status_code == 200
    env.client.cookies.clear()
    assert (
        await env.client.post("/api/admin/categories", json=body, headers=tma(ADMIN))
    ).status_code == 201
    # login ham Origin talab qiladi
    assert (
        await env.client.post("/api/auth/telegram-login", json=widget_data(ADMIN))
    ).status_code == 403


async def test_logout_revokes_session_and_expired_is_rejected(env):
    r = await login(env)
    token = token_of(r)
    env.client.cookies.set("savatcha_session", token)
    out = await env.client.post("/api/auth/logout", headers=ORIGIN)
    assert out.status_code == 204
    env.client.cookies.set("savatcha_session", token)
    assert (await env.client.get("/api/admin/orders")).status_code == 401
    assert (await env.client.get("/api/auth/session")).json()["authenticated"] is False

    r = await login(env)
    env.client.cookies.set("savatcha_session", token_of(r))
    async with env.sf() as s:
        for row in (await s.scalars(select(AdminSession))).all():
            row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        await s.commit()
    assert (await env.client.get("/api/admin/orders")).status_code == 401


async def test_logout_requires_allowed_origin(env):
    r = await login(env)
    env.client.cookies.set("savatcha_session", token_of(r))
    assert (await env.client.post("/api/auth/logout")).status_code == 403
    assert (await env.client.get("/api/admin/orders")).status_code == 200  # hali kirgan


async def test_audit_log_records_admin_actions(env):
    r = await login(env)
    env.client.cookies.set("savatcha_session", token_of(r))
    cat = (
        await env.client.post(
            "/api/admin/categories", json={"name_uz": "A", "name_ru": "Б"}, headers=ORIGIN
        )
    ).json()
    await env.client.patch(
        f"/api/admin/categories/{cat['id']}", json={"name_uz": "A2"}, headers=ORIGIN
    )
    await env.client.delete(f"/api/admin/categories/{cat['id']}", headers=ORIGIN)
    await env.client.get("/api/admin/orders/export.csv")
    await env.client.post("/api/auth/logout", headers=ORIGIN)
    async with env.sf() as s:
        logs = (await s.scalars(select(AuditLog).order_by(AuditLog.id))).all()
    assert [(x.action, x.entity) for x in logs] == [
        ("login", "session"),
        ("create", "category"),
        ("update", "category"),
        ("delete", "category"),
        ("export", "order"),
        ("logout", "session"),
    ]
    assert all(x.admin_tg_id == ADMIN for x in logs)
    env.client.cookies.clear()
    page = (await env.client.get("/api/admin/audit?action=create", headers=tma(ADMIN))).json()
    assert page["total"] == 1 and page["items"][0]["entity"] == "category"
    assert (await env.client.get("/api/admin/audit", headers=tma(CLIENT))).status_code == 403


async def _order(env, uid=CLIENT, items=((1, 2),), name="Ali Valiyev", phone="+998901234567"):
    for pid, qty in items:
        await env.client.put(f"/api/cart/items/{pid}", json={"quantity": qty}, headers=tma(uid))
    r = await env.client.post(
        "/api/orders",
        data={"customer_name": name, "phone": phone, "address": "Toshkent, Chilonzor"},
        files={"receipt": ("c.png", png_bytes(), "image/png")},
        headers=tma(uid),
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_orders_filters_sort_export_and_bulk(env):
    a = tma(ADMIN)
    o1 = await _order(env, CLIENT, ((1, 1),), name="Ali")
    o2 = await _order(env, OTHER, ((2, 3), (3, 1)), name="Vali", phone="+998931112233")
    o3 = await _order(env, OTHER, ((1, 1),), name="=cmd|' /C calc'!A0", phone="+998931112233")
    g = env.client.get
    assert (await g("/api/admin/orders?q=vali", headers=a)).json()["total"] == 1
    assert (await g("/api/admin/orders?q=931112233", headers=a)).json()["total"] == 2
    assert (await g(f"/api/admin/orders?q=%23{o1}", headers=a)).json()["items"][0]["id"] == o1
    assert (await g("/api/admin/orders?source=miniapp", headers=a)).json()["total"] == 3
    assert (await g("/api/admin/orders?source=classic", headers=a)).json()["total"] == 0
    assert (await g("/api/admin/orders?source=web", headers=a)).status_code == 422
    asc = (await g("/api/admin/orders?sort=total&dir=asc", headers=a)).json()["items"]
    assert [float(x["total"]) for x in asc] == sorted(float(x["total"]) for x in asc)
    assert (await g("/api/admin/orders?per_page=2&page=2", headers=a)).json()["items"][0][
        "id"
    ] == o1
    today = today_tashkent().isoformat()
    assert (await g(f"/api/admin/orders?from={today}&to={today}", headers=a)).json()["total"] == 3
    assert (await g("/api/admin/orders?to=2001-01-01", headers=a)).json()["total"] == 0

    # CSV: filtrga mos, formula in'ektsiyasidan himoyalangan
    csv_resp = await g("/api/admin/orders/export.csv?q=cmd", headers=a)
    assert csv_resp.headers["content-type"].startswith("text/csv")
    lines = csv_resp.text.lstrip("﻿").splitlines()
    assert len(lines) == 2 and lines[0].startswith("id,created_at")
    assert "'=cmd" in lines[1] and f",{o3}," not in lines[1][:2] and lines[1].startswith(f"{o3},")

    # ommaviy holat: ruxsat etilganlari o'tadi, qolgani failed da
    ok = await env.client.patch(
        "/api/admin/orders/bulk-status", json={"ids": [o1, o2], "status": "accepted"}, headers=a
    )
    assert ok.json() == {"updated": [o1, o2], "failed": []}
    mixed = await env.client.patch(
        "/api/admin/orders/bulk-status",
        json={"ids": [o1, o3, 9999], "status": "delivering"},
        headers=a,
    )
    assert mixed.json()["updated"] == [o1]
    assert {f["id"]: f["reason"] for f in mixed.json()["failed"]} == {
        o3: "invalid_transition",
        9999: "not_found",
    }
    assert any(getattr(c, "chat_id", None) == CLIENT for c in env.fake.calls)  # mijozga xabar
    bad = await env.client.patch(
        "/api/admin/orders/bulk-status", json={"ids": [o1], "status": "zzz"}, headers=a
    )
    assert bad.status_code == 422
    async with env.sf() as s:
        actions = [x.action for x in (await s.scalars(select(AuditLog))).all()]
    assert actions.count("status_change") == 2 and "export" in actions


async def test_categories_reorder_and_settings_and_sessions(env):
    a, c = tma(ADMIN), env.client
    cats = (await c.get("/api/admin/categories", headers=a)).json()
    ids = [x["id"] for x in cats]
    new_order = list(reversed(ids))
    assert (
        await c.patch("/api/admin/categories/reorder", json={"ids": new_order}, headers=a)
    ).status_code == 204
    assert [x["id"] for x in (await c.get("/api/admin/categories", headers=a)).json()] == new_order
    assert (
        await c.patch("/api/admin/categories/reorder", json={"ids": ids[:-1]}, headers=a)
    ).status_code == 422

    s = (await c.get("/api/admin/settings", headers=a)).json()
    assert s["notify_admin_ids"] == [] and s["admin_ids"] == [ADMIN]
    r = await c.patch(
        "/api/admin/settings",
        json={"shop_name": "Mening do'konim", "work_hours": "10-20"},
        headers=a,
    )
    assert r.json()["shop_name"] == "Mening do'konim"
    assert (
        await c.patch("/api/admin/settings", json={"notify_admin_ids": [12345]}, headers=a)
    ).status_code == 422
    assert (await c.get("/api/shop", headers=tma(CLIENT))).json()["shop_name"] == "Mening do'konim"
    assert (await c.get("/api/admin/settings", headers=tma(CLIENT))).status_code == 403

    login_resp = await login(env)
    env.client.cookies.set("savatcha_session", token_of(login_resp))
    sessions = (await c.get("/api/admin/sessions")).json()
    assert len(sessions) == 1 and sessions[0]["current"] is True
    assert (
        await c.delete(f"/api/admin/sessions/{sessions[0]['id']}", headers=ORIGIN)
    ).status_code == 204
    assert (await c.get("/api/admin/sessions")).status_code == 401  # o'zining sessiyasini o'chirdi


async def test_customers_list_search_sort_export_and_detail(env):
    a = tma(ADMIN)
    await _order(env, CLIENT, ((1, 1),), name="Ali")  # 12 000
    await _order(env, OTHER, ((2, 3),), name="Vali", phone="+998931112233")  # 15 000
    await _order(env, OTHER, ((1, 1),), name="Vali", phone="+998931112233")  # 12 000
    await env.client.get("/api/me", headers=tma(333))  # buyurtmasiz mijoz
    # tushum faqat accepted/delivering/done: yangi buyurtmalar jami summaga kirmaydi
    r = await env.client.patch(
        "/api/admin/orders/bulk-status", json={"ids": [1, 2, 3], "status": "accepted"}, headers=a
    )
    assert r.json()["updated"] == [1, 2, 3]
    c = env.client.get
    page = (await c("/api/admin/customers?sort=total_spent&dir=desc", headers=a)).json()
    assert page["total"] == 3 + 1  # + admin foydalanuvchisi (a tma bilan yaratildi)
    top = page["items"][0]
    assert top["tg_id"] == OTHER and top["orders_count"] == 2 and float(top["total_spent"]) == 27000
    # bekor qilingan buyurtma jami sarflangan summaga kirmaydi
    await env.client.patch("/api/admin/orders/3/status", json={"status": "cancelled"}, headers=a)
    top = (await c("/api/admin/customers?sort=total_spent", headers=a)).json()["items"][0]
    assert float(top["total_spent"]) == 15000 and top["orders_count"] == 2
    found = (await c("/api/admin/customers?search=u111", headers=a)).json()
    assert found["total"] == 1 and found["items"][0]["tg_id"] == CLIENT
    assert (await c("/api/admin/customers?search=%25", headers=a)).json()["total"] == 0
    csv_text = (await c("/api/admin/customers/export.csv", headers=a)).text
    assert csv_text.lstrip("﻿").startswith("id,name,username,phone")
    detail = (await c(f"/api/admin/customers/{top['id']}", headers=a)).json()
    assert detail["customer"]["tg_id"] == OTHER and len(detail["orders"]) == 2
    assert (await c("/api/admin/customers/99999", headers=a)).status_code == 404


async def test_stats_endpoints_admin_only_and_validate_range(env):
    a = tma(ADMIN)
    for path in (
        "summary", "sales-by-day", "orders-by-status", "by-source", "by-category", "by-hour",
        "new-customers", "top-products", "slow-products", "top-customers",
    ):  # fmt: skip
        assert (
            await env.client.get(f"/api/admin/stats/{path}", headers=tma(CLIENT))
        ).status_code == 403
        assert (await env.client.get(f"/api/admin/stats/{path}", headers=a)).status_code == 200, (
            path
        )
    bad = await env.client.get("/api/admin/stats/summary?from=2026-02-02&to=2026-01-01", headers=a)
    assert (bad.status_code, bad.json()["detail"]) == (422, "invalid_range")
    long = await env.client.get("/api/admin/stats/summary?from=2020-01-01&to=2026-01-01", headers=a)
    assert long.status_code == 422
    week = (await env.client.get("/api/admin/stats/sales-by-day", headers=a)).json()
    assert len(week) == 7 and all(d["orders"] == 0 for d in week)  # bo'sh kunlar 0 bilan
    top = await env.client.get("/api/admin/stats/top-products?by=bogus", headers=a)
    assert top.status_code == 422
