from datetime import datetime

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import SendMessage
from aiogram.types import Chat, Message, Update, User

from savatcha.api import gateway_bot
from savatcha.core.config import get_settings
from tests.fakes import FakeSession


@pytest.fixture
def dp_bot(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite://")
    monkeypatch.setenv("WEBAPP_URL", "https://shop.example.com")
    get_settings.cache_clear()
    gateway_bot.router._parent_router = None
    fake = FakeSession()
    dp = Dispatcher()
    dp.include_router(gateway_bot.router)
    yield dp, Bot("1:A", session=fake), fake
    get_settings.cache_clear()


async def _say(dp, bot, text, lang):
    msg = Message(
        message_id=1,
        date=datetime.now(),
        chat=Chat(id=5, type="private"),
        from_user=User(id=5, is_bot=False, first_name="Ali", language_code=lang),
        text=text,
    )
    await dp.feed_update(bot, Update(update_id=1, message=msg))


@pytest.mark.parametrize(("lang", "needle"), [("ru", "Открыть магазин"), ("uz", "Do'konni ochish")])
async def test_start_sends_webapp_button(dp_bot, lang, needle):
    dp, bot, fake = dp_bot
    await _say(dp, bot, "/start", lang)
    sent = [c for c in fake.calls if isinstance(c, SendMessage)][-1]
    button = sent.reply_markup.inline_keyboard[0][0]
    assert needle in button.text
    assert button.web_app.url == "https://shop.example.com"


async def test_help_has_button_too(dp_bot):
    dp, bot, fake = dp_bot
    await _say(dp, bot, "/help", "uz")
    sent = [c for c in fake.calls if isinstance(c, SendMessage)][-1]
    assert sent.reply_markup.inline_keyboard[0][0].web_app is not None
