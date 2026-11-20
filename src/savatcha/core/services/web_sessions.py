import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.core.db.models import AdminSession


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def create_session(
    session: AsyncSession, tg_id: int, ttl_hours: int, ip: str | None, user_agent: str | None
) -> tuple[str, AdminSession]:
    """Token faqat bir marta qaytadi (cookie ga); DB da faqat hash."""
    token = secrets.token_urlsafe(32)
    row = AdminSession(
        token_hash=hash_token(token),
        tg_id=tg_id,
        expires_at=datetime.now(UTC) + timedelta(hours=ttl_hours),
        ip=ip,
        user_agent=(user_agent or "")[:255] or None,
    )
    session.add(row)
    await session.commit()
    return token, row


async def get_valid(session: AsyncSession, token: str) -> AdminSession | None:
    return await session.scalar(
        select(AdminSession).where(
            AdminSession.token_hash == hash_token(token),
            AdminSession.expires_at > datetime.now(UTC),
        )
    )


async def delete_by_token(session: AsyncSession, token: str) -> bool:
    result = await session.execute(
        delete(AdminSession).where(AdminSession.token_hash == hash_token(token))
    )
    await session.commit()
    return bool(result.rowcount)


async def list_active(session: AsyncSession, tg_id: int) -> list[AdminSession]:
    rows = await session.scalars(
        select(AdminSession)
        .where(AdminSession.tg_id == tg_id, AdminSession.expires_at > datetime.now(UTC))
        .order_by(AdminSession.id.desc())
    )
    return list(rows.all())


async def revoke(session: AsyncSession, session_id: int, tg_id: int) -> bool:
    result = await session.execute(
        delete(AdminSession).where(AdminSession.id == session_id, AdminSession.tg_id == tg_id)
    )
    await session.commit()
    return bool(result.rowcount)


async def purge_expired(session: AsyncSession) -> None:
    await session.execute(delete(AdminSession).where(AdminSession.expires_at <= datetime.now(UTC)))
    await session.commit()
