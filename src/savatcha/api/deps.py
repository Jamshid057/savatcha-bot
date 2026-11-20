from collections.abc import AsyncIterator

from aiogram import Bot
from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.api.auth import InitDataError, validate_init_data
from savatcha.core.config import Settings, get_settings
from savatcha.core.db.models import User
from savatcha.core.repo import users


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session


def get_bots(request: Request) -> dict[str, Bot]:
    return request.app.state.bots


def settings_dep() -> Settings:
    return get_settings()


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
        raise HTTPException(401, "unauthorized")
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


async def require_admin(
    user: User = Depends(current_user), settings: Settings = Depends(settings_dep)
) -> User:
    if user.tg_id not in settings.admin_ids:
        raise HTTPException(403, "forbidden")
    return user
