# Savatcha

A Telegram store in two flavours, built on **one shared core and one database**:

| | **v1 — Classic bot** | **v2 — Mini App** |
|---|---|---|
| Experience | In-chat: buttons, cart, checkout | Mobile-app-like (React) |
| Admin | Inside the bot (`/admin`) | Inside the Mini App + in the browser (v2.1) |
| Pricing tier (for clients) | Cheaper, faster to deliver | Somewhat pricier, premium |
| Best for | Small shops, simple catalogs | Large catalogs, branded experience |
| Status | ✅ ready | ✅ ready (+ web admin v2.1) |

Both versions share the same business logic (`src/savatcha/core/services`).
The full technical specification is in [`TZ-telegram-shop-bot.md`](TZ-telegram-shop-bot.md) (written in Uzbek).

## v1 features

**Customer:** language (uz/ru), catalog (categories, pagination, search), product card (photo, quantity),
cart (stored in the DB), checkout (name → phone → address → comment → receipt photo → confirm),
order history, and automatic notifications when an order status changes.

**Admin (`/admin`, `ADMIN_IDS` only):** product and category CRUD (with photos), archiving,
in stock / out of stock, orders (filters, details, receipt, status history, status change → customer notification),
`/stats` (today and last 7 days, Tashkent time).

## v2 and v2.1 features

**Mini App (React + FastAPI):** Telegram `initData` is verified with HMAC; prices and totals are computed
on the server only. Tab bar, BackButton/MainButton, haptic feedback, Telegram theme, skeleton loading,
optimistic cart, receipt upload, orders with status history, uz/ru. Admin API: products (with photos),
categories, order management.

**Web admin (`/admin`, in the browser):** sign-in via Telegram Login Widget (no passwords), `HttpOnly + Secure +
SameSite=Strict` session cookie, CSRF protection (Origin check), login rate limiting, audit log, active sessions.
Dashboard (KPIs with comparison to the previous period, 6 charts), reports (top / slow-moving products,
top customers), orders table (server-side filtering/sorting, bulk status change, CSV export, printing),
products (inline price/availability editing), categories (drag-and-drop ordering), customers, settings.
New orders appear as a toast within 30 seconds.

## Getting started

```bash
cp .env.example .env     # fill in BOT_TOKEN_CLASSIC, ADMIN_IDS, POSTGRES_PASSWORD
                         # the password in DATABASE_URL must match POSTGRES_PASSWORD
docker compose --profile classic up -d --build
docker compose --profile classic run --rm bot python -m savatcha.core.seed   # demo data (optional)
```

**v2 (Mini App) and the web admin** need a domain for HTTPS. Set `SITE_ADDRESS`, `WEBAPP_URL`,
`BOT_TOKEN_APP` and `VITE_BOT_USERNAME` in `.env`, then configure the Mini App URL and `/setdomain` in BotFather:

```bash
docker compose --profile miniapp up -d --build
# both versions together (one shared DB): --profile classic --profile miniapp
```

The Telegram Login Widget only works on an HTTPS domain registered with `/setdomain`
(locally, use Cloudflare Tunnel or ngrok).
Database migrations (`alembic upgrade head`) run in a dedicated `migrate` service before the bot and API start.
Updating: `git pull && docker compose --profile classic up -d --build`.

### Local development

```bash
uv sync
uv run ruff check . && uv run ruff format --check . && uv run pytest
```

```bash
cd webapp && npm ci && npm run lint && npm test && npm run build
```

Tests run on SQLite and do not need a connection to Telegram (the bot flow is exercised with a fake session).
To run them against Postgres as well: `TEST_DATABASE_URL=postgresql+asyncpg://... uv run pytest`.

## Architecture

```
src/savatcha/
├── core/            # shared core
│   ├── config.py    # .env settings
│   ├── db/          # SQLAlchemy 2 (async) models
│   ├── repo/        # user queries
│   ├── services/    # catalog, cart, orders, files, notify, stats, formatting  <- business logic
│   ├── utils/       # phone, price, text helpers
│   └── locales/     # uz.json, ru.json
├── bot/             # v1: aiogram 3 (handlers only call services)
└── api/             # v2: FastAPI (auth, routers, admin/*) + gateway_bot.py
webapp/              # React + Vite + TS + Tailwind (Mini App and /admin)
deploy/Caddyfile     # HTTPS and security headers
migrations/          # Alembic (single, shared)
```

Conventions: money is `Decimal`; an order stores a snapshot of each product's name and price;
all user-facing text lives in `locales/*.json`; images are stored on disk
(`UPLOAD_DIR/products` is public, `UPLOAD_DIR/receipts` is private) with only the path kept in the DB;
admin rights are determined solely by `ADMIN_IDS`.

## Screenshots

> The demo bot (`@savatcha_classic_bot`), screenshots and a video will be added here.
