import os

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine

from savatcha.core.db import models  # noqa: F401
from savatcha.core.db.base import Base, make_session_factory


@pytest_asyncio.fixture
async def session():
    # TEST_DATABASE_URL (Postgres) berilsa SQL shoxchalari haqiqiy Postgres da ham sinaladi (CI).
    engine = create_async_engine(
        os.environ.get("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with make_session_factory(engine)() as s:
        yield s
    await engine.dispose()
