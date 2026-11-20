from datetime import datetime

from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import SendPhoto, TelegramMethod
from aiogram.types import Chat, Message, PhotoSize


class FakeSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[TelegramMethod] = []

    async def close(self) -> None: ...

    async def stream_content(self, *a, **k):  # pragma: no cover
        raise NotImplementedError

    async def make_request(self, bot: Bot, method: TelegramMethod, timeout=None):  # noqa: ASYNC109
        self.calls.append(method)
        name = type(method).__name__
        if name.startswith("Send"):
            photo = (
                [PhotoSize(file_id="FID", file_unique_id="u", width=1, height=1)]
                if isinstance(method, SendPhoto)
                else None
            )
            return Message(
                message_id=len(self.calls),
                date=datetime.now(),
                chat=Chat(id=getattr(method, "chat_id", 0), type="private"),
                text=getattr(method, "text", None),
                photo=photo,
            )
        return True

    def sent(self, chat_id: int) -> list[str]:
        out = []
        for c in self.calls:
            if getattr(c, "chat_id", None) == chat_id:
                out.append(getattr(c, "text", None) or getattr(c, "caption", None) or "")
        return out
