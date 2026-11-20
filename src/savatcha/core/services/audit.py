from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.core.db.models import AuditLog

ACTIONS = ("create", "update", "delete", "status_change", "login", "logout", "export")


async def log_action(
    session: AsyncSession,
    admin_tg_id: int,
    action: str,
    entity: str,
    entity_id: int | None = None,
    details: dict | None = None,
) -> None:
    """Admin amalini audit_log ga yozadi (alohida commit: asosiy amal muvaffaqiyatli bo'lgandan keyin)."""
    if action not in ACTIONS:
        raise ValueError(f"unknown audit action {action!r}")
    session.add(
        AuditLog(
            admin_tg_id=admin_tg_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            details=details,
        )
    )
    await session.commit()


async def list_logs(
    session: AsyncSession,
    *,
    action: str | None = None,
    admin_tg_id: int | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    page: int = 1,
    per_page: int = 30,
) -> tuple[list[AuditLog], int]:
    conds = []
    if action:
        conds.append(AuditLog.action == action)
    if admin_tg_id:
        conds.append(AuditLog.admin_tg_id == admin_tg_id)
    if start:
        conds.append(AuditLog.created_at >= start)
    if end:
        conds.append(AuditLog.created_at < end)
    total = await session.scalar(select(func.count(AuditLog.id)).where(*conds)) or 0
    rows = await session.scalars(
        select(AuditLog)
        .where(*conds)
        .order_by(AuditLog.id.desc())
        .limit(per_page)
        .offset((max(1, page) - 1) * per_page)
    )
    return list(rows.all()), int(total)
