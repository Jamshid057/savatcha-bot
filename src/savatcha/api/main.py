import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from aiogram import Bot
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from savatcha.api.limits import limiter
from savatcha.api.routers import auth, cart, catalog, me, orders, shop
from savatcha.api.routers.admin import router as admin_router
from savatcha.core.config import get_settings
from savatcha.core.db.base import make_engine, make_session_factory
from savatcha.core.services.files import PRODUCTS_SUBDIR

log = logging.getLogger(__name__)


def create_app(
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    bots: dict[str, Bot] | None = None,
) -> FastAPI:
    """Testlarda `session_factory` va `bots` tashqaridan beriladi (lifespan ishlamaydi)."""
    settings = get_settings()
    dev = settings.app_env == "dev"

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = None
        if app.state.session_factory is None:
            engine = make_engine(settings.database_url)
            app.state.session_factory = make_session_factory(engine)
        if app.state.bots is None:
            app.state.bots = {
                source: Bot(token)
                for source, token in (
                    ("classic", settings.bot_token_classic),
                    ("miniapp", settings.bot_token_app),
                )
                if token
            }
        try:
            yield
        finally:
            for bot in app.state.bots.values():
                await bot.session.close()
            if engine is not None:
                await engine.dispose()

    app = FastAPI(
        title="Savatcha API",
        lifespan=lifespan,
        docs_url="/docs" if dev else None,
        redoc_url=None,
        openapi_url="/openapi.json" if dev else None,
    )
    app.state.session_factory = session_factory
    app.state.bots = bots
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    if settings.webapp_url:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[settings.webapp_url.rstrip("/")],
            allow_methods=["*"],
            allow_headers=["Authorization", "Content-Type"],
        )

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth.router, prefix="/api")
    app.include_router(me.router, prefix="/api")
    app.include_router(shop.router, prefix="/api")
    app.include_router(catalog.router, prefix="/api")
    app.include_router(cart.router, prefix="/api")
    app.include_router(orders.router, prefix="/api")
    app.include_router(admin_router, prefix="/api")

    # Faqat mahsulot rasmlari ochiq; cheklar (receipts/) hech qachon.
    products_dir = Path(settings.upload_dir) / PRODUCTS_SUBDIR
    products_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/files", StaticFiles(directory=products_dir), name="files")
    return app


def app_factory() -> FastAPI:
    return create_app()
