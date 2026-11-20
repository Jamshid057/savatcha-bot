from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.api.deps import (
    SESSION_COOKIE,
    get_session,
    require_admin,
    settings_dep,
)
from savatcha.api.schemas import SettingsPatch
from savatcha.core.config import Settings
from savatcha.core.db.models import User
from savatcha.core.services import audit, shop_settings, web_sessions

router = APIRouter()


@router.get("/settings")
async def get_settings(
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_dep),
):
    return {**await shop_settings.get_all(session, settings), "admin_ids": settings.admin_ids}


@router.patch("/settings")
async def patch_settings(
    body: SettingsPatch,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_dep),
):
    changes = body.model_dump(exclude_none=True)
    if "notify_admin_ids" in changes and not set(changes["notify_admin_ids"]) <= set(
        settings.admin_ids
    ):
        raise HTTPException(422, "invalid_admin_ids")
    await shop_settings.update(session, changes)
    await audit.log_action(session, admin.tg_id, "update", "settings", None, changes)
    return {**await shop_settings.get_all(session, settings), "admin_ids": settings.admin_ids}


@router.get("/sessions")
async def list_sessions(
    request: Request,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    token = request.cookies.get(SESSION_COOKIE)
    current = web_sessions.hash_token(token) if token else None
    rows = await web_sessions.list_active(session, admin.tg_id)
    return [
        {
            "id": r.id,
            "created_at": r.created_at,
            "expires_at": r.expires_at,
            "ip": r.ip,
            "user_agent": r.user_agent,
            "current": r.token_hash == current,
        }
        for r in rows
    ]


@router.delete("/sessions/{session_id}", status_code=204)
async def revoke_session(
    session_id: int,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    if not await web_sessions.revoke(session, session_id, admin.tg_id):
        raise HTTPException(404, "not_found")
    await audit.log_action(session, admin.tg_id, "delete", "session", session_id)
