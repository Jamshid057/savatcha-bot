"""Telegram Mini App `initData` tekshiruvi (HMAC-SHA256)."""

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl


class InitDataError(Exception):
    pass


@dataclass(frozen=True)
class TgUser:
    id: int
    full_name: str
    username: str | None
    language_code: str | None


def validate_init_data(init_data: str, bot_token: str, max_age_seconds: int) -> TgUser:
    """Imzo, `auth_date` yoshi va `user` ni tekshirib, foydalanuvchini qaytaradi."""
    if not init_data or not bot_token:
        raise InitDataError("empty")
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise InitDataError("no hash")
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise InitDataError("bad signature")
    try:
        auth_date = int(pairs["auth_date"])
    except (KeyError, ValueError) as exc:
        raise InitDataError("bad auth_date") from exc
    if time.time() - auth_date > max_age_seconds:
        raise InitDataError("expired")
    try:
        user = json.loads(pairs["user"])
        tg_id = int(user["id"])
    except (KeyError, ValueError, TypeError) as exc:
        raise InitDataError("bad user") from exc
    full_name = " ".join(p for p in (user.get("first_name"), user.get("last_name")) if p)
    return TgUser(tg_id, full_name or str(tg_id), user.get("username"), user.get("language_code"))
