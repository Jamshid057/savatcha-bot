from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.core.db.models import User


async def get_by_tg_id(session: AsyncSession, tg_id: int) -> User | None:
    return await session.scalar(select(User).where(User.tg_id == tg_id))


async def get_or_create(
    session: AsyncSession, tg_id: int, full_name: str, username: str | None
) -> User:
    user = await get_by_tg_id(session, tg_id)
    if user is None:
        user = User(tg_id=tg_id, full_name=full_name, username=username)
        session.add(user)
    elif user.full_name != full_name or user.username != username:
        user.full_name = full_name
        user.username = username
    else:
        return user
    await session.commit()
    return user


async def set_lang(session: AsyncSession, user: User, lang: str) -> None:
    user.lang = lang
    await session.commit()


async def set_phone(session: AsyncSession, user: User, phone: str) -> None:
    user.phone = phone
    await session.commit()
