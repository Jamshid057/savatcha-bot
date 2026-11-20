# Savatcha

Telegram do'kon, ikki ko'rinishda — **bitta yadro, bitta ma'lumotlar bazasi**:

| | **v1 — Classic bot** | **v2 — Mini App** |
|---|---|---|
| Tajriba | Chat ichida: tugmalar, savat, buyurtma | Mobil ilovaga o'xshash (React) |
| Admin | Botning ichida (`/admin`) | Mini App ichida + brauzerda (v2.1) |
| Narx (mijozga) | Arzonroq, tezroq | Biroz qimmatroq, premium |
| Mos mijoz | Kichik do'kon, oddiy katalog | Ko'p mahsulot, brend tajribasi |
| Holat | ✅ tayyor | rejada |

Ikkala versiya bir xil biznes-mantiqdan (`src/savatcha/core/services`) foydalanadi.
To'liq texnik topshiriq: [`TZ-telegram-shop-bot.md`](TZ-telegram-shop-bot.md).

## v1 imkoniyatlari

**Mijoz:** til (uz/ru), katalog (kategoriya, sahifalash, qidiruv), mahsulot kartasi (rasm, miqdor),
savat (DB da saqlanadi), buyurtma (ism → telefon → manzil → izoh → chek rasmi → tasdiq),
buyurtmalarim va holat o'zgarsa avtomatik xabar.

**Admin (`/admin`, faqat `ADMIN_IDS`):** mahsulot va kategoriya CRUD (rasm bilan), arxivlash,
mavjud/tugagan, buyurtmalar (filtr, tafsilot, chek, holat tarixi, holat o'zgartirish → mijozga xabar),
`/stats` (bugun va 7 kun, Toshkent vaqti bilan).

## Ishga tushirish

```bash
cp .env.example .env     # BOT_TOKEN_CLASSIC, ADMIN_IDS, POSTGRES_PASSWORD ni to'ldiring
                         # DATABASE_URL dagi parol POSTGRES_PASSWORD bilan bir xil bo'lsin
docker compose --profile classic up -d --build
docker compose --profile classic run --rm bot python -m savatcha.core.seed   # demo ma'lumot (ixtiyoriy)
```

### Lokal ishlab chiqish

```bash
uv sync
uv run ruff check . && uv run ruff format --check . && uv run pytest
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
└── bot/             # v1: aiogram 3 (handlerlar faqat servislarni chaqiradi)
migrations/          # Alembic (bitta, umumiy)
```

Qoidalar: pul `Decimal`; buyurtmada nom va narx nusxalanadi (snapshot); matnlar faqat `locales/*.json`;
rasmlar diskda (`UPLOAD_DIR/products` ochiq, `UPLOAD_DIR/receipts` yopiq), DB da faqat yo'l;
admin huquqi faqat `ADMIN_IDS` orqali.

## Skrinshotlar

> Demo bot (`@savatcha_classic_bot`), skrinshotlar va video joylanadi (A10, qo'lda).
