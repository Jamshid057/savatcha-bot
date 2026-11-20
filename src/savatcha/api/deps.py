from collections.abc import AsyncIterator
from urllib.parse import urlsplit

from aiogram import Bot
from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.api.auth import InitDataError, validate_init_data
from savatcha.core.config import Settings, get_settings
from savatcha.core.db.models import User
from savatcha.core.repo import users
from savatcha.core.services import web_sessions


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session


def get_bots(request: Request) -> dict[str, Bot]:
    return request.app.state.bots


def settings_dep() -> Settings:
    return get_settings()


SESSION_COOKIE = "savatcha_session"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def allowed_origins(settings: Settings) -> set[str]:
    origins = {settings.webapp_url.rstrip("/")} if settings.webapp_url else set()
    if settings.app_env == "dev":
        origins |= {"http://localhost:5173", "http://localhost:8000", "http://127.0.0.1:5173"}
    return origins


def check_csrf(request: Request, settings: Settings) -> None:
    """Cookie bilan o'zgartiruvchi so'rovlar faqat ruxsat etilgan Origin/Referer dan."""
    origin = request.headers.get("origin")
    if origin is None:
        referer = request.headers.get("referer", "")
        parts = urlsplit(referer)
        origin = f"{parts.scheme}://{parts.netloc}" if parts.scheme and parts.netloc else None
    if origin is None or origin.rstrip("/") not in allowed_origins(settings):
        raise HTTPException(403, "csrf")


def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return forwarded or (request.client.host if request.client else None)


def init_data_from_header(request: Request) -> str | None:
    scheme, _, value = request.headers.get("Authorization", "").partition(" ")
    return value if scheme.lower() == "tma" and value else None


async def current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_dep),
) -> User:
    init_data = init_data_from_header(request)
    if init_data is None:
        return await _user_from_cookie(request, session, settings)
    try:
        tg = validate_init_data(
            init_data, settings.bot_token_app, settings.initdata_max_age_seconds
        )
    except InitDataError as exc:
        raise HTTPException(401, "unauthorized") from exc
    user = await users.get_or_create(session, tg.id, tg.full_name, tg.username)
    if user.lang is None and tg.language_code:
        await users.set_lang(session, user, "ru" if tg.language_code.startswith("ru") else "uz")
    return user


async def _user_from_cookie(request: Request, session: AsyncSession, settings: Settings) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    row = await web_sessions.get_valid(session, token) if token else None
    if row is None or row.tg_id not in settings.admin_ids:
        raise HTTPException(401, "unauthorized")
    if request.method not in SAFE_METHODS:
        check_csrf(request, settings)
    user = await users.get_by_tg_id(session, row.tg_id)
    if user is None:
        raise HTTPException(401, "unauthorized")
    return user


async def require_admin(
    user: User = Depends(current_user), settings: Settings = Depends(settings_dep)
) -> User:
    if user.tg_id not in settings.admin_ids:
        raise HTTPException(403, "forbidden")
    return user
