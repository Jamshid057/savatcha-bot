from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.api.deps import get_session, require_admin
from savatcha.core.services import audit
from savatcha.core.services.stats import range_bounds

router = APIRouter(prefix="/audit", dependencies=[Depends(require_admin)])


@router.get("")
async def list_audit(
    action: str | None = Query(default=None, max_length=32),
    admin: int | None = None,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=30, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    start = range_bounds(date_from, date_from)[0] if date_from else None
    end = range_bounds(date_to, date_to)[1] if date_to else None
    rows, total = await audit.list_logs(
        session,
        action=action,
        admin_tg_id=admin,
        start=start,
        end=end,
        page=page,
        per_page=per_page,
    )
    return {
        "items": [
            {
                "id": r.id,
                "admin_tg_id": r.admin_tg_id,
                "action": r.action,
                "entity": r.entity,
                "entity_id": r.entity_id,
                "details": r.details,
                "created_at": r.created_at,
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "pages": max(1, -(-total // per_page)),
    }
