import logging
from datetime import UTC
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.api.deps import (
    SESSION_COOKIE,
    check_csrf,
    client_ip,
    get_session,
    settings_dep,
)
from savatcha.api.limits import limiter
from savatcha.api.web_auth import LoginError, verify_login_widget
from savatcha.core.config import Settings
from savatcha.core.repo import users
from savatcha.core.services import audit, web_sessions

log = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def _set_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        secure=settings.app_env != "dev",
        samesite="strict",
        path="/",
    )


@router.post("/telegram-login")
@limiter.limit("5/minute")
async def telegram_login(
    request: Request,
    response: Response,
    data: dict[str, Any] = Body(...),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_dep),
):
    check_csrf(request, settings)
    ip = client_ip(request)
    try:
        tg_id = verify_login_widget(data, settings.bot_token_app)
    except LoginError as exc:
        log.warning("Telegram login rad etildi (%s) ip=%s", exc, ip)
        raise HTTPException(401, "unauthorized") from exc
    if tg_id not in settings.admin_ids:
        log.warning("Telegram login: admin emas id=%s ip=%s", tg_id, ip)
        raise HTTPException(403, "forbidden")
    name = " ".join(str(data[k]) for k in ("first_name", "last_name") if data.get(k)) or str(tg_id)
    await users.get_or_create(session, tg_id, name, data.get("username"))
    token, row = await web_sessions.create_session(
        session, tg_id, settings.session_ttl_hours, ip, request.headers.get("user-agent")
    )
    await audit.log_action(session, tg_id, "login", "session", row.id, {"ip": ip})
    _set_cookie(response, token, settings)
    return {"authenticated": True, "tg_id": tg_id, "expires_at": row.expires_at}


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_dep),
):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        check_csrf(request, settings)
        row = await web_sessions.get_valid(session, token)
        await web_sessions.delete_by_token(session, token)
        if row is not None:
            await audit.log_action(session, row.tg_id, "logout", "session", row.id)
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/session")
async def get_session_state(
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_dep),
):
    token = request.cookies.get(SESSION_COOKIE)
    row = await web_sessions.get_valid(session, token) if token else None
    if row is None or row.tg_id not in settings.admin_ids:
        return {"authenticated": False, "tg_id": None, "expires_at": None}
    expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=UTC)
    return {"authenticated": True, "tg_id": row.tg_id, "expires_at": expires}
