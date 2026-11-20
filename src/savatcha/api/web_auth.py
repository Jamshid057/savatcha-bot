"""Telegram Login Widget (brauzer) tekshiruvi."""

import hashlib
import hmac
import time
from collections.abc import Mapping
from typing import Any

LOGIN_MAX_AGE_SECONDS = 300


class LoginError(Exception):
    pass


def verify_login_widget(
    data: Mapping[str, Any], bot_token: str, max_age: int = LOGIN_MAX_AGE_SECONDS
) -> int:
    """Widget ma'lumotini tekshirib, Telegram id ni qaytaradi. Imzo: HMAC-SHA256, secret = SHA256(token)."""
    received = str(data.get("hash", ""))
    if not received or not bot_token:
        raise LoginError("no hash")
    check_string = "\n".join(f"{k}={data[k]}" for k in sorted(data) if k != "hash")
    secret = hashlib.sha256(bot_token.encode()).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        raise LoginError("bad signature")
    try:
        auth_date = int(data["auth_date"])
        tg_id = int(data["id"])
    except (KeyError, ValueError, TypeError) as exc:
        raise LoginError("bad fields") from exc
    if time.time() - auth_date > max_age:
        raise LoginError("expired")
    return tg_id
