# Savatcha

Telegram do'kon, ikki ko'rinishda — **bitta yadro, bitta ma'lumotlar bazasi**:

| | **v1 — Classic bot** | **v2 — Mini App** |
|---|---|---|
| Tajriba | Chat ichida: tugmalar, savat, buyurtma | Mobil ilovaga o'xshash (React) |
| Admin | Botning ichida (`/admin`) | Mini App ichida + brauzerda (v2.1) |
| Narx (mijozga) | Arzonroq, tezroq | Biroz qimmatroq, premium |
| Mos mijoz | Kichik do'kon, oddiy katalog | Ko'p mahsulot, brend tajribasi |
| Holat | ✅ tayyor | ✅ tayyor |

Ikkala versiya bir xil biznes-mantiqdan (`src/savatcha/core/services`) foydalanadi.
To'liq texnik topshiriq: [`TZ-telegram-shop-bot.md`](TZ-telegram-shop-bot.md).

## v1 imkoniyatlari

**Mijoz:** til (uz/ru), katalog (kategoriya, sahifalash, qidiruv), mahsulot kartasi (rasm, miqdor),
savat (DB da saqlanadi), buyurtma (ism → telefon → manzil → izoh → chek rasmi → tasdiq),
buyurtmalarim va holat o'zgarsa avtomatik xabar.

**Admin (`/admin`, faqat `ADMIN_IDS`):** mahsulot va kategoriya CRUD (rasm bilan), arxivlash,
mavjud/tugagan, buyurtmalar (filtr, tafsilot, chek, holat tarixi, holat o'zgartirish → mijozga xabar),
`/stats` (bugun va 7 kun, Toshkent vaqti bilan).

## v2 imkoniyatlari

**Mini App (React + FastAPI):** Telegram `initData` HMAC bilan tekshiriladi, narx/summa faqat serverda hisoblanadi.
Tab bar, BackButton/MainButton, haptic, Telegram temasi, skeleton, optimistik savat, chek yuklash,
buyurtmalar va holat tarixi, uz/ru. Admin API: mahsulot (rasm), kategoriya, buyurtma boshqaruvi.

## Ishga tushirish

```bash
cp .env.example .env     # BOT_TOKEN_CLASSIC, ADMIN_IDS, POSTGRES_PASSWORD ni to'ldiring
                         # DATABASE_URL dagi parol POSTGRES_PASSWORD bilan bir xil bo'lsin
docker compose --profile classic up -d --build
docker compose --profile classic run --rm bot python -m savatcha.core.seed   # demo ma'lumot (ixtiyoriy)
```

**v2 (Mini App)** (HTTPS uchun domen kerak, `.env` da `SITE_ADDRESS`, `WEBAPP_URL`,
`BOT_TOKEN_APP`; BotFather da Mini App URL va `/setdomain`):

```bash
docker compose --profile miniapp up -d --build
# ikkalasi birga (bitta umumiy DB): --profile classic --profile miniapp
```

Mini App faqat HTTPS da ochiladi (lokalda Cloudflare Tunnel/ngrok).
Migratsiyalar (`alembic upgrade head`) alohida `migrate` servisida bot/api dan oldin bajariladi.
Yangilash: `git pull && docker compose --profile classic up -d --build`.

### Lokal ishlab chiqish

```bash
uv sync
uv run ruff check . && uv run ruff format --check . && uv run pytest
```

```bash
cd webapp && npm ci && npm run lint && npm test && npm run build
```

Testlar SQLite da ishlaydi; Telegram'ga ulanish shart emas (bot oqimi soxta sessiya bilan sinaladi).
Postgres da ham ishga tushirish: `TEST_DATABASE_URL=postgresql+asyncpg://... uv run pytest`.

## Arxitektura

```
src/savatcha/
├── core/            # umumiy yadro
│   ├── config.py    # .env sozlamalari
│   ├── db/          # SQLAlchemy 2 (async) modellari
│   ├── repo/        # foydalanuvchi so'rovlari
│   ├── services/    # catalog, cart, orders, files, notify, stats, formatting  <- biznes-mantiq
│   ├── utils/       # telefon, narx, matn
│   └── locales/     # uz.json, ru.json
├── bot/             # v1: aiogram 3 (handlerlar faqat servislarni chaqiradi)
└── api/             # v2: FastAPI (auth, routers, admin/*) + gateway_bot.py
webapp/              # React + Vite + TS + Tailwind (Mini App va /admin)
deploy/Caddyfile     # HTTPS, xavfsizlik headerlari
migrations/          # Alembic (bitta, umumiy)
```

Qoidalar: pul `Decimal`; buyurtmada nom va narx nusxalanadi (snapshot); matnlar faqat `locales/*.json`;
rasmlar diskda (`UPLOAD_DIR/products` ochiq, `UPLOAD_DIR/receipts` yopiq), DB da faqat yo'l;
admin huquqi faqat `ADMIN_IDS` orqali.

## Skrinshotlar

> Demo bot (`@savatcha_classic_bot`), skrinshotlar va video joylanadi (A10, qo'lda).
