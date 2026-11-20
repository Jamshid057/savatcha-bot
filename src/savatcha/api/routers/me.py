from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.api.deps import current_user, get_session, settings_dep
from savatcha.api.schemas import UserOut, UserPatch, user_out
from savatcha.core.config import Settings
from savatcha.core.db.models import User
from savatcha.core.repo import users
from savatcha.core.utils.phone import normalize_phone

router = APIRouter(tags=["me"])


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(current_user), settings: Settings = Depends(settings_dep)):
    return user_out(user, settings.admin_ids)


@router.patch("/me", response_model=UserOut)
async def patch_me(
    body: UserPatch,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_dep),
):
    if body.lang is not None:
        await users.set_lang(session, user, body.lang)
    if body.phone is not None:
        phone = normalize_phone(body.phone)
        if phone is None:
            raise HTTPException(422, "invalid_phone")
        await users.set_phone(session, user, phone)
    return user_out(user, settings.admin_ids)
