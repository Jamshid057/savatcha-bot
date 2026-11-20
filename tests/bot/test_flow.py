"""Bot oqimi: haqiqiy Dispatcher + SQLite, Telegram o'rniga soxta sessiya."""

from datetime import datetime
from decimal import Decimal

import pytest_asyncio
from aiogram import Bot
from aiogram.methods import AnswerCallbackQuery, SendPhoto
from aiogram.types import CallbackQuery, Chat, Contact, Message, Update, User
from sqlalchemy.ext.asyncio import create_async_engine

from savatcha.bot.keyboards.admin import AdminCB, AdmOrderCB
from savatcha.bot.keyboards.cart import CartCB, ConfirmCB
from savatcha.bot.keyboards.catalog import AddCB, CatCB, ProdCB
from savatcha.bot.keyboards.lang import LangCB
from savatcha.bot.main import build_dispatcher
from savatcha.core.config import get_settings
from savatcha.core.db import models  # noqa: F401
from savatcha.core.db.base import Base, make_session_factory
from savatcha.core.db.models import Order
from savatcha.core.seed import seed
from tests.fakes import FakeSession

ADMIN, CLIENT = 999, 111


def _detach_routers() -> None:
    """Handler modullaridagi routerlar bitta Dispatcher'ga bog'lanadi; har testda bo'shatamiz."""
    from savatcha.bot.handlers import admin, cart, catalog, checkout, fallback, menu, start
    from savatcha.bot.handlers import orders as my_orders

    for r in [start.router, menu.router, *admin.routers, catalog.router, cart.router,
              my_orders.router, checkout.router, fallback.router]:  # fmt: skip
        r._parent_router = None


class Harness:
    def __init__(self, dp, bot, fake):
        self.dp, self.bot, self.fake, self.n = dp, bot, fake, 0

    def _user(self, uid: int) -> User:
        return User(id=uid, is_bot=False, first_name="Ali", last_name="V", username=f"u{uid}")

    async def say(self, uid: int, text: str | None = None, **extra) -> None:
        self.n += 1
        msg = Message(
            message_id=self.n,
            date=datetime.now(),
            chat=Chat(id=uid, type="private"),
            from_user=self._user(uid),
            text=text,
            **extra,
        )
        await self.dp.feed_update(self.bot, Update(update_id=self.n, message=msg))

    async def press(self, uid: int, data) -> None:
        self.n += 1
        # Tugma bosilgan xabar: oxirgi yuborilgan xabar (matn bo'lsa)
        base = Message(
            message_id=self.n,
            date=datetime.now(),
            chat=Chat(id=uid, type="private"),
            from_user=User(id=1, is_bot=True, first_name="bot"),
            text="x",
        )
        cq = CallbackQuery(
            id=str(self.n),
            from_user=self._user(uid),
            chat_instance="ci",
            message=base,
            data=data.pack(),
        )
        await self.dp.feed_update(self.bot, Update(update_id=self.n, callback_query=cq))

    def last_text(self, chat_id: int) -> str:
        return self.fake.sent(chat_id)[-1]


@pytest_asyncio.fixture
async def h(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path}/t.db")
    monkeypatch.setenv("ADMIN_IDS", str(ADMIN))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "up"))
    monkeypatch.setenv("REQUIRE_RECEIPT", "false")
    get_settings.cache_clear()
    engine = create_async_engine(get_settings().database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sf = make_session_factory(engine)
    async with sf() as s:
        await seed(s, get_settings().upload_dir)
    fake = FakeSession()
    bot = Bot("123:ABC", session=fake)
    _detach_routers()
    dp = build_dispatcher(sf, bot)
    yield Harness(dp, bot, fake), sf
    await engine.dispose()
    get_settings.cache_clear()


async def test_full_customer_to_admin_flow(h):
    harness, sf = h
    fake = harness.fake
    # /start -> til tanlash -> menyu
    await harness.say(CLIENT, "/start")
    assert "Tilni tanlang" in harness.last_text(CLIENT)
    await harness.press(CLIENT, LangCB(code="ru"))
    assert "Здравствуйте" in harness.last_text(CLIENT)

    # katalog -> kategoriya -> mahsulot -> savatga
    await harness.say(CLIENT, "🛍 Каталог")
    assert "Выберите категорию" in harness.last_text(CLIENT)
    await harness.press(CLIENT, CatCB(id=1))
    await harness.press(CLIENT, ProdCB(id=1))
    assert any(isinstance(c, SendPhoto) for c in fake.calls)  # rasm bilan karta
    await harness.press(CLIENT, AddCB(id=1, q=2))
    answers = [c for c in fake.calls if isinstance(c, AnswerCallbackQuery) and c.text]
    assert "2" in answers[-1].text
    await harness.say(CLIENT, "🛒 Корзина")
    assert "Coca-Cola 1.5л × 2 = 24 000 сум" in harness.last_text(CLIENT)

    # checkout FSM (REQUIRE_RECEIPT=false)
    await harness.press(CLIENT, CartCB(act="checkout"))
    await harness.say(CLIENT, "Ali Valiyev")
    await harness.say(CLIENT, "123")  # noto'g'ri telefon
    assert "Неверный номер" in harness.last_text(CLIENT)
    await harness.say(
        CLIENT, None, contact=Contact(phone_number="998901234567", first_name="A", user_id=CLIENT)
    )
    await harness.say(CLIENT, "Toshkent, Chilonzor 5")
    await harness.say(CLIENT, "⏭ Пропустить")  # izoh
    await harness.say(CLIENT, "⏭ Пропустить")  # chek (ixtiyoriy)
    assert "Проверьте заказ" in harness.last_text(CLIENT)
    await harness.press(CLIENT, ConfirmCB(ok=True))
    assert "Заказ #1 принят" in " ".join(fake.sent(CLIENT))
    # adminga xabar keldi (inline tugmalar bilan)
    admin_msgs = [c for c in fake.calls if getattr(c, "chat_id", None) == ADMIN]
    assert admin_msgs and "Новый заказ" not in admin_msgs[-1].text  # admin tili: uz
    assert "Yangi buyurtma" in admin_msgs[-1].text and admin_msgs[-1].reply_markup

    async with sf() as s:
        order = await s.get(Order, 1)
        assert order.source == "classic" and order.total == Decimal("24000.00")

    # admin: /admin, buyurtmani qabul qilish -> mijozga xabar
    await harness.say(ADMIN, "/admin")
    assert "Admin panel" in harness.last_text(ADMIN)
    await harness.press(ADMIN, AdminCB(act="orders"))
    await harness.press(ADMIN, AdmOrderCB(act="st", id=1, s="accepted"))
    assert "Принят" in harness.last_text(CLIENT)
    # noto'g'ri o'tish rad etiladi
    await harness.press(ADMIN, AdmOrderCB(act="st", id=1, s="done"))
    async with sf() as s:
        assert (await s.get(Order, 1)).status == "accepted"


async def test_non_admin_cannot_use_admin(h):
    harness, _ = h
    await harness.say(CLIENT, "/start")
    await harness.say(CLIENT, "/admin")
    assert "Нет доступа" in harness.last_text(CLIENT) or "Ruxsat yo'q" in harness.last_text(CLIENT)
    n = len(harness.fake.calls)
    await harness.press(CLIENT, AdminCB(act="orders"))  # callback e'tiborsiz qoladi
    assert all(
        getattr(c, "chat_id", None) != CLIENT or "Buyurtmalar" not in (getattr(c, "text", "") or "")
        for c in harness.fake.calls[n:]
    )


async def test_menu_button_cancels_checkout_state(h):
    harness, _ = h
    await harness.say(CLIENT, "/start")
    await harness.press(CLIENT, LangCB(code="uz"))
    await harness.press(CLIENT, AddCB(id=1, q=1))
    await harness.press(CLIENT, CartCB(act="checkout"))
    await harness.say(CLIENT, "🛍 Katalog")  # ism sifatida qabul qilinmasligi kerak
    assert "Kategoriyani tanlang" in harness.last_text(CLIENT)
    await harness.say(CLIENT, "Salom")  # endi hech qaysi holatda emas: javob yo'q
    assert harness.last_text(CLIENT) == "Kategoriyani tanlang:"


async def test_admin_category_and_product_crud(h):
    from sqlalchemy import select

    from savatcha.bot.keyboards.admin import AdmCatCB, AdmProdCB
    from savatcha.core.db.models import Category, Product

    harness, sf = h
    await harness.say(ADMIN, "/admin")

    # kategoriya qo'shish
    await harness.press(ADMIN, AdmCatCB(act="add"))
    await harness.say(ADMIN, "Yangi kat")
    await harness.say(ADMIN, "Новая кат")
    async with sf() as s:
        cat = await s.scalar(select(Category).where(Category.name_uz == "Yangi kat"))
    assert cat is not None and cat.name_ru == "Новая кат"

    # ichi bo'sh kategoriya o'chiriladi
    await harness.press(ADMIN, AdmCatCB(act="del_ok", id=cat.id))
    async with sf() as s:
        assert await s.get(Category, cat.id) is None
    # ichida mahsuloti bor kategoriya o'chmaydi
    await harness.press(ADMIN, AdmCatCB(act="del_ok", id=1))
    async with sf() as s:
        assert await s.get(Category, 1) is not None

    # mahsulot qo'shish (rasmsiz)
    await harness.press(ADMIN, AdmProdCB(act="add", cat=1))
    for text in ("Test mahsulot", "Тест товар", "Tavsif", "Описание", "abc"):
        await harness.say(ADMIN, text)
    assert "Narx noto'g'ri" in harness.last_text(ADMIN)  # "abc" narx emas
    await harness.say(ADMIN, "15 000")
    await harness.say(ADMIN, "-")
    async with sf() as s:
        p = await s.scalar(select(Product).where(Product.name_uz == "Test mahsulot"))
    assert p is not None and p.price == Decimal("15000.00") and p.image_path is None

    # narxni tahrirlash, mavjudlik, arxiv
    await harness.press(ADMIN, AdmProdCB(act="edit", id=p.id, f="price"))
    await harness.say(ADMIN, "-5")
    assert "Narx noto'g'ri" in harness.last_text(ADMIN)
    await harness.say(ADMIN, "17500")
    await harness.press(ADMIN, AdmProdCB(act="avail", id=p.id))
    await harness.press(ADMIN, AdmProdCB(act="arch_ok", id=p.id))
    async with sf() as s:
        p = await s.get(Product, p.id)
    assert p.price == Decimal("17500.00") and p.is_archived and not p.is_available
