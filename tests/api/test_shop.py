from decimal import Decimal

from sqlalchemy import select

from savatcha.core.db.models import Order, Product
from tests.api.conftest import ADMIN, CLIENT, OTHER, png_bytes, tma

FORM = {"customer_name": "Ali Valiyev", "phone": "+998901234567", "address": "Toshkent, Chilonzor"}


async def _fill_cart(env, uid=CLIENT):
    await env.client.put("/api/cart/items/1", json={"quantity": 2}, headers=tma(uid))
    await env.client.put("/api/cart/items/2", json={"quantity": 1}, headers=tma(uid))


async def test_catalog_pagination_search_and_unavailable(env):
    h = tma(CLIENT)
    cats = (await env.client.get("/api/categories", headers=h)).json()
    assert len(cats) == 5
    page = (await env.client.get("/api/products?per_page=5&page=2", headers=h)).json()
    assert page["total"] == 19 and page["pages"] == 4 and len(page["items"]) == 5
    found = (await env.client.get("/api/products?q=cola", headers=h)).json()
    assert [p["name_uz"] for p in found["items"]] == ["Coca-Cola 1.5L"]
    assert found["items"][0]["image_url"].startswith("/files/")
    assert (await env.client.get("/api/products/9999", headers=h)).status_code == 404
    img = found["items"][0]["image_url"]
    assert (await env.client.get(img)).status_code == 200  # ochiq mahsulot rasmi


async def test_cart_server_side_total_and_isolation(env):
    await _fill_cart(env)
    cart = (await env.client.get("/api/cart", headers=tma(CLIENT))).json()
    assert Decimal(cart["total"]) == Decimal("12000") * 2 + Decimal("5000")
    assert (await env.client.get("/api/cart", headers=tma(OTHER))).json()["lines"] == []
    r = await env.client.put("/api/cart/items/1", json={"quantity": 0}, headers=tma(CLIENT))
    assert len(r.json()["lines"]) == 1
    r = await env.client.put("/api/cart/items/999", json={"quantity": 1}, headers=tma(CLIENT))
    assert r.status_code == 409
    r = await env.client.put("/api/cart/items/1", json={"quantity": -1}, headers=tma(CLIENT))
    assert r.status_code == 422
    assert (await env.client.delete("/api/cart", headers=tma(CLIENT))).json()["lines"] == []


async def test_order_total_computed_on_server_and_admin_notified(env):
    await _fill_cart(env)
    files = {"receipt": ("c.png", png_bytes(), "image/png")}
    r = await env.client.post(
        "/api/orders", data={**FORM, "total": "1"}, files=files, headers=tma(CLIENT)
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert Decimal(body["total"]) == Decimal("29000") and body["source"] == "miniapp"
    assert body["has_receipt"] and [h["to_status"] for h in body["history"]] == ["new"]
    sent = [c for c in env.fake.calls if getattr(c, "chat_id", None) == ADMIN]
    assert sent and f"#{body['id']}" in sent[0].text
    # savat tozalandi, buyurtmalar ro'yxatida bor
    assert (await env.client.get("/api/cart", headers=tma(CLIENT))).json()["lines"] == []
    mine = (await env.client.get("/api/orders", headers=tma(CLIENT))).json()
    assert [o["id"] for o in mine["items"]] == [body["id"]]


async def test_order_validation(env):
    await _fill_cart(env)
    h = tma(CLIENT)
    png = {"receipt": ("c.png", png_bytes(), "image/png")}
    r = await env.client.post("/api/orders", data=FORM, headers=h)
    assert (r.status_code, r.json()["detail"]) == (422, "receipt_required")
    r = await env.client.post("/api/orders", data={**FORM, "phone": "123"}, files=png, headers=h)
    assert (r.status_code, r.json()["detail"]) == (422, "invalid_phone")
    bad = {"receipt": ("c.gif", png_bytes("GIF"), "image/gif")}
    r = await env.client.post("/api/orders", data=FORM, files=bad, headers=h)
    assert (r.status_code, r.json()["detail"]) == (400, "image_type")
    junk = {"receipt": ("c.png", b"not an image", "image/png")}
    r = await env.client.post("/api/orders", data=FORM, files=junk, headers=h)
    assert (r.status_code, r.json()["detail"]) == (400, "image_invalid")
    # xatolardan keyin savat saqlanadi, bo'sh savat bilan buyurtma bo'lmaydi
    assert len((await env.client.get("/api/cart", headers=h)).json()["lines"]) == 2
    r = await env.client.post("/api/orders", data=FORM, files=png, headers=tma(OTHER))
    assert (r.status_code, r.json()["detail"]) == (409, "empty_cart")


async def test_receipt_access_only_owner_and_admin(env):
    await _fill_cart(env)
    files = {"receipt": ("c.png", png_bytes(), "image/png")}
    oid = (
        await env.client.post("/api/orders", data=FORM, files=files, headers=tma(CLIENT))
    ).json()["id"]
    assert (
        await env.client.get(f"/api/orders/{oid}/receipt", headers=tma(CLIENT))
    ).status_code == 200
    assert (
        await env.client.get(f"/api/orders/{oid}/receipt", headers=tma(OTHER))
    ).status_code == 404
    assert (await env.client.get(f"/api/orders/{oid}", headers=tma(OTHER))).status_code == 404
    assert (
        await env.client.get(f"/api/admin/orders/{oid}/receipt", headers=tma(ADMIN))
    ).status_code == 200
    assert (await env.client.get(f"/api/orders/{oid}/receipt")).status_code == 401
    # cheklar ochiq /files orqali berilmaydi
    async with env.sf() as s:
        path = (await s.get(Order, oid)).receipt_path
    assert (await env.client.get("/files/" + path.split("/", 1)[1])).status_code == 404
    assert (await env.client.get("/files/../" + path)).status_code in (404, 400)


async def test_admin_order_status_flow_and_customer_notified(env):
    await _fill_cart(env)
    files = {"receipt": ("c.png", png_bytes(), "image/png")}
    oid = (
        await env.client.post("/api/orders", data=FORM, files=files, headers=tma(CLIENT))
    ).json()["id"]
    a = tma(ADMIN)
    lst = (await env.client.get("/api/admin/orders?status=new", headers=a)).json()
    assert lst["total"] == 1
    r = await env.client.patch(
        f"/api/admin/orders/{oid}/status", json={"status": "done"}, headers=a
    )
    assert (r.status_code, r.json()["detail"]) == (409, "invalid_transition")
    r = await env.client.patch(
        f"/api/admin/orders/{oid}/status", json={"status": "accepted"}, headers=a
    )
    assert r.json()["status"] == "accepted" and r.json()["history"][-1]["changed_by_tg_id"] == ADMIN
    assert any(getattr(c, "chat_id", None) == CLIENT for c in env.fake.calls)  # mijozga xabar
    assert (await env.client.get("/api/admin/orders?status=bogus", headers=a)).status_code == 422


async def test_admin_category_and_product_crud(env):
    a, c = tma(ADMIN), env.client
    cat = (
        await c.post(
            "/api/admin/categories", json={"name_uz": "Yangi", "name_ru": "Новая"}, headers=a
        )
    ).json()
    assert (
        await c.patch(f"/api/admin/categories/{cat['id']}", json={"name_uz": "Yangi2"}, headers=a)
    ).json()["name_uz"] == "Yangi2"

    data = {"category_id": str(cat["id"]), "name_uz": "Olma", "name_ru": "Яблоко", "price": "9 500"}
    r = await c.post(
        "/api/admin/products",
        data=data,
        files={"image": ("a.png", png_bytes(), "image/png")},
        headers=a,
    )
    assert r.status_code == 201, r.text
    p = r.json()
    assert Decimal(p["price"]) == Decimal("9500") and p["image_url"].startswith("/files/")
    assert (await c.get(p["image_url"])).status_code == 200

    bad = await c.post("/api/admin/products", data={**data, "price": "-1"}, headers=a)
    assert (bad.status_code, bad.json()["detail"]) == (422, "invalid_price")
    bad = await c.post("/api/admin/products", data={**data, "category_id": "9999"}, headers=a)
    assert (bad.status_code, bad.json()["detail"]) == (422, "invalid_category")
    bad = await c.post(
        "/api/admin/products",
        data=data,
        files={"image": ("a.gif", png_bytes("GIF"), "image/gif")},
        headers=a,
    )
    assert bad.json()["detail"] == "image_type"

    r = await c.patch(
        f"/api/admin/products/{p['id']}",
        data={"price": "11000", "is_available": "false"},
        headers=a,
    )
    assert Decimal(r.json()["price"]) == Decimal("11000") and r.json()["is_available"] is False
    # kategoriya ichida mahsulot bor: o'chmaydi
    assert (await c.delete(f"/api/admin/categories/{cat['id']}", headers=a)).status_code == 409
    assert (await c.delete(f"/api/admin/products/{p['id']}", headers=a)).status_code == 204
    async with env.sf() as s:
        assert (await s.scalar(select(Product).where(Product.id == p["id"]))).is_archived
    assert (await c.get(f"/api/products/{p['id']}", headers=tma(CLIENT))).status_code == 404
    # arxivlangan mahsulot bor: kategoriya baribir o'chmaydi
    assert (await c.delete(f"/api/admin/categories/{cat['id']}", headers=a)).status_code == 409
