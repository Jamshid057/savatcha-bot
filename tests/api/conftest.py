import hashlib
import hmac
import io
import json
import time
from urllib.parse import urlencode

import httpx
import pytest_asyncio
from aiogram import Bot
from PIL import Image
from sqlalchemy.ext.asyncio import create_async_engine

from savatcha.api.limits import limiter
from savatcha.api.main import create_app
from savatcha.core.config import get_settings
from savatcha.core.db import models  # noqa: F401
from savatcha.core.db.base import Base, make_session_factory
from savatcha.core.seed import seed
from tests.fakes import FakeSession

TOKEN_APP = "111:APPTOKEN"
ADMIN, CLIENT, OTHER = 999, 111, 222


def make_init_data(
    user_id: int,
    *,
    token: str = TOKEN_APP,
    auth_date: int | None = None,
    first_name: str = "Ali",
    tamper: bool = False,
    lang: str = "uz",
) -> str:
    """Telegram Mini App imzolagan initData ni taqlid qiladi."""
    user = {
        "id": user_id,
        "first_name": first_name,
        "username": f"u{user_id}",
        "language_code": lang,
    }
    fields = {
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": "AAH",
        "user": json.dumps(user, separators=(",", ":")),
    }
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if tamper:
        fields["user"] = fields["user"].replace(str(user_id), "1")
    return urlencode(fields)


def tma(user_id: int, **kw) -> dict[str, str]:
    return {"Authorization": f"tma {make_init_data(user_id, **kw)}"}


def png_bytes(fmt: str = "PNG") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (30, 30), (10, 120, 200)).save(buf, fmt)
    return buf.getvalue()


class ApiEnv:
    def __init__(self, client, sf, fake):
        self.client, self.sf, self.fake = client, sf, fake


@pytest_asyncio.fixture
async def env(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path}/t.db")
    monkeypatch.setenv("ADMIN_IDS", str(ADMIN))
    monkeypatch.setenv("BOT_TOKEN_APP", TOKEN_APP)
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "up"))
    monkeypatch.setenv("REQUIRE_RECEIPT", "true")
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("WEBAPP_URL", "https://shop.example.com")
    get_settings.cache_clear()
    limiter.reset()
    engine = create_async_engine(get_settings().database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sf = make_session_factory(engine)
    async with sf() as s:
        await seed(s, get_settings().upload_dir)
    fake = FakeSession()
    app = create_app(sf, {"miniapp": Bot(TOKEN_APP, session=fake)})
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield ApiEnv(client, sf, fake)
    await engine.dispose()
    get_settings.cache_clear()
