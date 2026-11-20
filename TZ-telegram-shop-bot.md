# TZ: Savatcha — Telegram do'kon (v1 Classic bot + v2 Mini App + v2.1 Veb admin)

> v5 (v4 dagi kamchiliklar tuzatildi: holat tarixi, tushum ta'rifi, fayl papkalari, umumiy DB, ADMIN_IDS, xabarnoma xatolari, kategoriya o'chirish). Bitta loyiha, uch qatlam, **umumiy yadro** bilan:
> - **v1 — Classic bot:** hamma narsa botning ichida (inline tugmalar, FSM, admin ham botda).
> - **v2 — Mini App:** `/start` → "Do'konni ochish" → mobil ilova kabi veb-ilova (React + FastAPI).
> - **v2.1 — Veb admin (C qism, ixtiyoriy):** brauzerda ochiladigan kengaytirilgan admin panel (dashboard, grafiklar, top mahsulotlar, mijozlar, eksport).
>
> Ketma-ketlik: avval **Yadro + A qism (v1)**, tugagach tag `v1.0-classic`, keyin **B qism (v2)**, tag `v2.0-miniapp`, oxirida **C qism**, tag `v2.1-web-admin`.
> Claude CLI da ishlash uchun yozilgan: har bosqich alohida topshiriq.

---

## 0. Umumiy ma'lumot

| | |
|---|---|
| Loyiha nomi | **Savatcha** |
| GitHub repo | `savatcha-bot` (bitta monorepo) |
| Botlar | Ikkita alohida bot (BotFather da): `@savatcha_classic_bot` (v1), `@savatcha_app_bot` (v2). Band bo'lsa `_uz` / `_demo` qo'shing |
| Til | Python 3.12 |
| DB | PostgreSQL 16 |
| ORM / migratsiya | SQLAlchemy 2 (async) + Alembic |
| Bot | aiogram 3 (long polling) |
| v2 backend | FastAPI |
| v2 frontend | React 18 + Vite + TypeScript + Tailwind CSS |
| Konteyner | Docker Compose (profillar: `classic`, `miniapp`) |
| Test | pytest, pytest-asyncio, httpx; frontend: vitest (minimal) |
| Kod sifati | ruff (backend), ESLint (frontend) |
| CI | GitHub Actions |
| Interfeys tili | O'zbek (lotin) + rus |
| Muddat | v1: 7–10 kun, v2: yana 8–10 kun, v2.1 (C qism): yana 6–8 kun |
| Grafiklar | Recharts (frontend), SQL agregatlar (backend) |
| Jadvallar | TanStack Table |

**Maqsad:** portfolio. Ikki usulni ko'rsatish: arzon, oddiy mijozlar uchun classic bot va premium tajriba uchun Mini App. Ikkala versiya bir xil biznes-mantiq va bir xil ma'lumotlar modelidan foydalanadi.

---

## 1. Umumiy tuzilma (monorepo)

```
savatcha-bot/
├── src/savatcha/
│   ├── core/                   # YADRO: ikkala versiya uchun umumiy
│   │   ├── config.py           # sozlamalar (.env, pydantic-settings)
│   │   ├── db/ (base.py, models.py)
│   │   ├── repo/               # DB funksiyalari (users, catalog, cart, orders)
│   │   ├── services/           # savat, buyurtma yaratish, rasm saqlash, xabarnoma (notify.py)
│   │   ├── i18n.py + locales/  # xabarnoma va bot matnlari (uz.json, ru.json)
│   │   └── utils/              # telefon validatsiya, narx formatlash
│   ├── bot/                    # v1: classic bot (aiogram)
│   │   ├── main.py
│   │   ├── handlers/           # start, catalog, cart, checkout, orders, admin/*
│   │   ├── keyboards/, states.py, middlewares/
│   └── api/                    # v2: FastAPI (core dan foydalanadi)
│       ├── main.py, auth.py, schemas.py
│       ├── routers/            # me, catalog, cart, orders, admin/*
│       └── gateway_bot.py      # v2 uchun yengil bot: /start + WebApp tugmasi
├── webapp/                     # v2: React Mini App
├── migrations/                 # Alembic (bitta, umumiy)
├── tests/ (core/, bot/, api/)
├── deploy/Caddyfile
├── docker-compose.yml
├── pyproject.toml
├── .github/workflows/ci.yml
├── .env.example
├── .gitignore
└── README.md
```

### 1.1 Yadro (core) qoidalari
- **Biznes-mantiq faqat `core/services` da.** Bot handler'lari va API routerlari faqat ularni chaqiradi (hech qanday summa/narx hisobi handler ichida bo'lmasin).
- Bitta DB sxemasi, bitta Alembic migratsiya.
- Pul uchun `Decimal` / `Numeric` (float emas).
- Buyurtma yaratilganda nom va narx `order_items` ga **nusxalanadi** (snapshot).
- Matnlar faqat `locales/*.json` (uz, ru); kodda qattiq yozilmasin.
- **Rasmlar va cheklar diskda saqlanadi**, ikki alohida papkada: `UPLOAD_DIR/products/` (ochiq, `/files/*` orqali beriladi) va `UPLOAD_DIR/receipts/` (yopiq, faqat himoyalangan endpoint orqali; Caddy uni hech qachon bermaydi). DB da faqat yo'l. Classic bot admin yoki mijoz Telegram'ga rasm yuborsa, bot uni yuklab olib diskga saqlaydi (`services/files.py`); shunda v2 ham o'sha rasmlarni ko'rsata oladi. Tezlik uchun `tg_file_id` ham keshlanadi.
- Xabarnoma (`services/notify.py`): `notify_admins_new_order`, `notify_user_status_changed`. Buyurtma qaysi bot orqali kelgan bo'lsa (`orders.source`), xabar o'sha bot tokeni bilan yuboriladi. Yuborish xatosi (foydalanuvchi botni bloklagan yoki hech qachon `/start` qilmagan: `TelegramForbiddenError`, `TelegramBadRequest`) ushlanadi va logga yoziladi; buyurtma yaratilishi yoki holat o'zgarishi bundan bekor bo'lmaydi.
- **Admin huquqi faqat `ADMIN_IDS` (.env) orqali aniqlanadi** (`tg_id ∈ ADMIN_IDS`), DB da `is_admin` maydoni yo'q.
- **DB:** ikkala bot (v1 `classic` va v2 `miniapp`) **bitta umumiy DB** ga ulanadi. v1 va v2 bir mahsulotning ikki tarifi: mijozga ko'rsatish uchun v1 arzon (oddiy bot), v2 biroz qimmatroq (Mini App). Shu sababli mijoz, savat, katalog va buyurtmalar umumiy; `orders.source` buyurtma qaysi botdan kelganini ajratadi.

### 1.2 Ma'lumotlar modeli
```
users        id, tg_id (unique), full_name, username, lang, phone, created_at
categories   id, name_uz, name_ru, sort_order, is_active
products     id, category_id→categories, name_uz, name_ru, description_uz, description_ru,
             price (numeric), image_path, tg_file_id, is_available, is_archived, created_at
cart_items   id, user_id→users, product_id→products, quantity   (unique: user_id+product_id)
orders       id, user_id→users, source ('classic'|'miniapp'), status, customer_name, phone,
             address, comment, receipt_path, total (numeric), created_at
order_items  id, order_id→orders, product_id→products, name_snapshot, price_snapshot, quantity
order_status_history  id, order_id→orders, from_status (null = yaratilgan), to_status,
                      changed_by_tg_id (null = tizim/mijoz), created_at
```
Buyurtma holatlari: `new → accepted → delivering → done` yoki `cancelled`.
Har holat o'zgarishi (yaratish ham) `core/services` da `order_status_history` ga yoziladi; admin yon panelida to'liq tarix ko'rinadi.
Mahsulot buyurtmada ishlatilgan bo'lsa, haqiqiy o'chirilmaydi, `is_archived=true`.
Kategoriya: ichida mahsulot (arxivlangani ham) bo'lmasa o'chiriladi; bo'lsa faqat `is_active=false` qilinadi (o'chirish rad etiladi, tushunarli xabar bilan).

### 1.3 Sozlamalar (`.env.example`)
```
DATABASE_URL=postgresql+asyncpg://savatcha:***@db:5432/savatcha
BOT_TOKEN_CLASSIC=
BOT_TOKEN_APP=
ADMIN_IDS=123456789,987654321
REQUIRE_RECEIPT=true
UPLOAD_DIR=/data/uploads                      # ichida products/ va receipts/
MAX_UPLOAD_MB=5
WEBAPP_URL=https://savatcha.example.com      # v2
INITDATA_MAX_AGE_SECONDS=86400                # v2
SESSION_TTL_HOURS=12                          # v2.1
STATS_REVENUE_STATUSES=accepted,delivering,done   # v2.1 (/stats botda ham)
LOG_LEVEL=INFO
```

### 1.4 Nofunksional talablar (umumiy)
- Backend/bot `async`, type hint, `ruff` toza.
- Sirlar faqat `.env` da; repoda yo'q; `.env.example` bor.
- Xatolar ushlanadi, foydalanuvchiga tushunarli xabar, serverda log.
- Fayl yuklash: faqat `jpeg/png/webp`, hajm limiti (5 MB), nomi tasodifiy (uuid), rasm `Pillow` bilan siqiladi.
- Demo ma'lumotlar (seed skript): 4–5 kategoriya, 15–20 mahsulot (rasm bilan).

---

# A QISM — v1: CLASSIC BOT

Hamma narsa botning ichida. Admin panel ham botda.

## A1. Rollar
1. **Mijoz:** katalog, savat, buyurtma.
2. **Admin:** `ADMIN_IDS` dagi foydalanuvchilar; `/admin` orqali boshqaruv.

## A2. Mijoz funksiyalari

**Start va til**
- `/start`: salomlashish, til tanlash (O'zbekcha / Русский), tanlov DB da.
- Asosiy menyu (reply keyboard): 🛍 Katalog, 🛒 Savat, 📦 Buyurtmalarim, ⚙️ Til, ☎️ Aloqa.

**Katalog**
- Kategoriyalar (inline tugmalar) → mahsulotlar ro'yxati, sahifalash (5 ta), `◀️ ▶️`.
- Mahsulot kartasi: rasm, nom, tavsif, narx, "Mavjud / Tugagan", tugmalar `➖ 1 ➕` va `🛒 Savatga`.
- Qidiruv: "🔎 Qidirish" → matn kiritiladi → nom bo'yicha (`ILIKE`).

**Savat**
- Ko'rish, miqdorni `➕/➖`, o'chirish, jami summa; faqat "Mavjud" mahsulotlar.
- Savat DB da saqlanadi.

**Buyurtma (checkout, FSM)**
- ism → telefon (kontakt tugmasi yoki matn, validatsiya `+998XXXXXXXXX`) → manzil → izoh (o'tkazib yuborish mumkin) → chek rasmi (`REQUIRE_RECEIPT` ga qarab) → tasdiqlash.
- Yaratilgach: mijozga raqam bilan tasdiq; adminlarga xabar (inline: ✅ Qabul qilish, ❌ Bekor qilish).

**Buyurtmalarim**
- Ro'yxat va holat; holat o'zgarsa avtomatik xabar.

## A3. Admin panel (botning ichida)
Kirish: `/admin` (faqat `ADMIN_IDS`; boshqalarga "ruxsat yo'q"). Tekshiruv filter/middleware orqali, har handler'da takrorlanmaydi.

- **Mahsulotlar:** ➕ qo'shish (FSM: kategoriya → nom uz → nom ru → tavsif → narx → rasm), ✏️ tahrirlash, 🔁 mavjud/tugagan, 🗑 arxivlash (tasdiqlash bilan).
- **Kategoriyalar:** qo'shish, nomini o'zgartirish, o'chirish (ichi bo'sh bo'lsa).
- **Buyurtmalar:** filtr (yangi/jarayonda/tugagan/bekor), tafsilot (mijoz, telefon, manzil, tarkib, summa, chek rasmi), holatni o'zgartirish → mijozga xabar.
- **Statistika (ixtiyoriy):** `/stats` bugungi/haftalik buyurtma soni va summa.

## A4. Texnik qoidalar (v1)
- `CallbackData` factory'lari (matn parse qilmaslik).
- Sahifalash va holatlar uchun alohida klaviatura funksiyalari.
- Telegram cheklovlari hisobga olinadi: callback `answer()` har doim chaqiriladi, uzun matn bo'linadi.

## A5. Bosqichlar (v1)

| # | Bosqich | Natija |
|---|---|---|
| A1 | Skelet: monorepo, `pyproject.toml`, `core/config`, DB ulash, Docker Compose (`db`, `bot`), `/start` + til tanlash | Bot ishga tushadi, DB ga yozadi |
| A2 | Modellar + Alembic migratsiya + seed | `alembic upgrade head` va demo ma'lumot |
| A3 | Admin: kategoriya va mahsulot CRUD (FSM), rasm saqlash | Admin mahsulot qo'sha oladi |
| A4 | Mijoz: katalog, sahifalash, qidiruv | Mahsulotlar ko'rinadi |
| A5 | Savat (servis + handler) | Qo'shish, miqdor, o'chirish |
| A6 | Checkout (FSM) + chek yuklash + adminga xabarnoma | Buyurtma yaratiladi |
| A7 | Admin: buyurtmalar, holat o'zgartirish, mijozga xabar | To'liq oqim |
| A8 | Testlar + ruff + GitHub Actions | CI yashil |
| A9 | Docker Compose `classic` profili, VPS ga deploy | Bot internetda ishlaydi |
| A10 | README (skrinshotlar, video), demo bot, tag `v1.0-classic` | v1 portfolioga tayyor |

## A6. Qabul qilish mezonlari (v1)
- [ ] Mijoz katalogdan mahsulot tanlab, savat orqali buyurtma bera oladi (chek bilan).
- [ ] Admin botning ichidan mahsulot (rasm bilan), kategoriya va buyurtmalarni boshqara oladi.
- [ ] Yangi buyurtma adminga keladi; holat o'zgarsa mijozga xabar boradi.
- [ ] Til tanlash (uz/ru) ishlaydi; savat va buyurtmalar bot qayta ishga tushganda saqlanadi.
- [ ] Oddiy foydalanuvchi `/admin` ga kira olmaydi.
- [ ] `docker compose --profile classic up -d` bilan toza serverda ishga tushadi.
- [ ] Testlar o'tadi, CI yashil, repoda sirlar yo'q.
- [ ] README + ishlayotgan demo bot (`@savatcha_classic_bot`).

---

# B QISM — v2: TELEGRAM MINI APP

Bot faqat kirish eshigi va xabarnoma yuboruvchi. Hamma narsa Mini App ichida.
**Yadro (DB, servislar, xabarnoma) v1 dan qayta ishlatiladi**, yangi yoziladigan narsa: API, gateway bot, frontend.

## B1. Arxitektura

```
Foydalanuvchi (Telegram)
   │  /start  →  [🛍 Do'konni ochish]  (WebApp tugmasi)
   ▼
Mini App (React, https://savatcha.example.com)
   │  Authorization: tma <initData>      ← har so'rovda
   ▼
Caddy (HTTPS)  ── /        → statik frontend (dist/)
               ── /api/*   → FastAPI (api:8000)
               ── /files/* → faqat UPLOAD_DIR/products/ (cheklar emas)
   ▼
FastAPI ──► core/services ──► PostgreSQL
   └──► notify.py ──► Telegram Bot API (adminga yangi buyurtma, mijozga holat)
Gateway bot (aiogram, alohida jarayon): /start, /help, menyu tugmasi
```
- Frontend faqat `/api` bilan gaplashadi, Telegram'ga to'g'ridan-to'g'ri emas.
- `orders.source = 'miniapp'`; xabarnoma `BOT_TOKEN_APP` bilan yuboriladi.

## B2. Autentifikatsiya va xavfsizlik
1. Mini App `window.Telegram.WebApp.initData` ni oladi; har so'rovda `Authorization: tma <initData>`.
2. Server tekshiradi: HMAC-SHA256 (`secret = HMAC("WebAppData", BOT_TOKEN_APP)`), `hash` mos; `auth_date` `INITDATA_MAX_AGE_SECONDS` dan eski emas; `user` dan `tg_id`, ism, username olinadi; DB da yaratiladi/yangilanadi.
3. Admin: har so'rovda `tg_id ∈ ADMIN_IDS` tekshiriladi (DB da `is_admin` yo'q). Admin endpoint'lari `Depends(require_admin)`.
4. Mijoz faqat o'z savati/buyurtmasini ko'radi.
5. Narx va summa **serverda** hisoblanadi.
6. Chek rasmlariga (`receipts/`) faqat admin va buyurtma egasi kira oladi (himoyalangan endpoint; ochiq `/files` faqat `products/` ni beradi).
7. CORS faqat Mini App domeniga; rate limit (`slowapi`) buyurtma va yuklash endpoint'larida.
8. `/docs` faqat dev rejimida ochiq.

## B3. Gateway bot
- `/start`: salomlashish + inline tugma **"🛍 Do'konni ochish"** (`WebAppInfo(url=WEBAPP_URL)`).
- `MenuButtonWebApp` o'rnatiladi (ham BotFather, ham kod orqali).
- `/help`: qisqa yo'riqnoma. Til `language_code` dan taxmin qilinadi, ilovada o'zgartiriladi.

## B4. Mini App — mijoz (mobil ilova kabi)

**Tuyg'u (muhim):**
- Pastda **tab bar**: 🏠 Bosh, 🔎 Qidiruv, 🛒 Savat (badge), 📦 Buyurtmalar, 👤 Profil.
- Telegram `themeParams` (yorug/qorong'i) CSS o'zgaruvchilar orqali.
- Telegram **BackButton** ichki sahifalarda; **MainButton** ("Savatga qo'shish", "Buyurtma berish", "Tasdiqlash").
- `WebApp.ready()`, `expand()`, kerak bo'lsa `disableVerticalSwipes()`.
- **Haptic feedback**, **skeleton** yuklanish, "Qayta urinish" xato holatida, yengil animatsiya, safe-area.
- Rasmlar lazy loading.

**Sahifalar**
- **Bosh:** kategoriya chiplari + mahsulotlar to'ri (2 ustun).
- **Katalog/Qidiruv:** kategoriya filtri, nom bo'yicha qidiruv (debounce 300 ms), sahifalash/infinite scroll.
- **Mahsulot:** rasm, nom, tavsif, narx, miqdor, "Savatga qo'shish".
- **Savat:** miqdor, o'chirish, jami; serverda saqlanadi; UI optimistik.
- **Checkout:** ism (Telegramdan), telefon (validatsiya), manzil, izoh, chek yuklash (kamera/galereya); muvaffaqiyat ekrani.
- **Buyurtmalar:** ro'yxat, tafsilot, rangli holat belgisi.
- **Profil:** til (uz/ru), telefon.

## B5. Mini App — admin (faqat `is_admin`)
Profilda "⚙️ Admin" bo'limi (mijozga ko'rinmaydi): mahsulot CRUD (uz/ru nom va tavsif, narx, kategoriya, **rasm yuklash**, mavjudlik, arxivlash), kategoriya CRUD, buyurtmalar (filtr, tafsilot, chek, holat o'zgartirish → xabarnoma), statistika (ixtiyoriy).

## B6. API (asosiy endpoint'lar)
Hammasi `Authorization: tma <initData>` talab qiladi (health bundan mustasno).

| Metod | Yo'l | Tavsif |
|---|---|---|
| GET | `/api/health` | Salomatlik |
| GET / PATCH | `/api/me` | Joriy foydalanuvchi / til, telefon |
| GET | `/api/categories` | Kategoriyalar |
| GET | `/api/products?category=&q=&page=` | Mahsulotlar |
| GET | `/api/products/{id}` | Mahsulot |
| GET | `/api/cart` | Savat |
| PUT | `/api/cart/items/{product_id}` | Miqdor (0 = o'chirish) |
| DELETE | `/api/cart` | Savatni tozalash |
| POST | `/api/orders` | Buyurtma (multipart: forma + chek) |
| GET | `/api/orders`, `/api/orders/{id}` | Mening buyurtmalarim |
| POST/PATCH/DELETE | `/api/admin/products`, `/api/admin/categories` | CRUD (rasm yuklash bilan) |
| GET | `/api/admin/orders?status=` | Barcha buyurtmalar |
| PATCH | `/api/admin/orders/{id}/status` | Holat (+ xabarnoma) |
| GET | `/api/admin/orders/{id}/receipt` | Chek rasmi |

## B7. Frontend tuzilmasi (`webapp/`)
```
src/
├── main.tsx, App.tsx
├── api/                 # fetch klient (tma header), tiplar
├── pages/               # Home, Catalog, Product, Cart, Checkout, Orders, Profile, admin/*
├── components/          # TabBar, ProductCard, Skeleton, QuantityStepper...
├── lib/telegram.ts      # WebApp o'rami (ready, expand, MainButton, BackButton, haptic, theme)
├── i18n/ (uz.json, ru.json)
└── store/               # zustand + TanStack Query
```
TypeScript `strict`, ESLint toza, mobil birinchi (360–430 px).

## B8. Deploy (v2)
- Docker Compose `miniapp` profili: `db`, `api`, `bot` (gateway), `web` (Caddy: frontend + `/api` proxy + HTTPS). `restart: unless-stopped`; `alembic upgrade head` `api` dan oldin.
- **HTTPS shart** (Mini App faqat HTTPS da ochiladi): VPS + domen/subdomen A yozuvi → Caddy avtomatik sertifikat. Dev/vaqtinchalik: Cloudflare Tunnel yoki ngrok.
- BotFather: Mini App URL / Menu Button sozlash.
- Yangilash: `git pull && docker compose --profile miniapp up -d --build`.
- v1 va v2 bir VPS da birga ishlaydi va **bitta DB** dan foydalanadi (bitta `db` servisi, ikkala profil unga ulanadi). Dashboarddagi "Classic vs Mini App" grafigi shu sababli to'liq ishlaydi.

## B9. Bosqichlar (v2)

| # | Bosqich | Natija |
|---|---|---|
| B1 | `api/` skeleti (FastAPI, core dan foydalanish), `auth.py` (initData) + `/api/me` + testlar | Faqat Telegram'dan kirish mumkin |
| B2 | Gateway bot: `/start` + WebApp tugmasi + menyu tugmasi | Tugma Mini App'ni ochadi (dev tunnel) |
| B3 | `webapp/` skeleti: Vite + React + TS + Tailwind, `lib/telegram.ts`, tema, TabBar, i18n, API klient | Mobil ilova "qobig'i" |
| B4 | Katalog API + Bosh/Katalog/Qidiruv/Mahsulot sahifalari | Mahsulotlar ko'rinadi |
| B5 | Savat API + sahifa (MainButton, haptic) | Savat ishlaydi |
| B6 | Checkout + chek yuklash + buyurtma API + xabarnoma | Buyurtma yaratiladi |
| B7 | Buyurtmalar sahifasi + holat xabarnomasi | Mijoz kuzatadi |
| B8 | Admin sahifalari: mahsulot/kategoriya CRUD (rasm), buyurtmalar | Admin to'liq boshqaradi |
| B9 | Testlar to'ldirish, ESLint/ruff, CI ga frontend build qo'shish | CI yashil |
| B10 | Caddy HTTPS, VPS deploy, BotFather, README (skrinshot, video), tag `v2.0-miniapp` | v2 portfolioga tayyor |

## B10. Qabul qilish mezonlari (v2)
- [ ] Botda `/start` → "Do'konni ochish" → Mini App ochiladi, foydalanuvchi avtomatik tanilgan.
- [ ] Telegram temasi, tab bar, BackButton, MainButton ishlaydi.
- [ ] Katalog, qidiruv, mahsulot, savat, checkout, chek yuklash ishlaydi.
- [ ] Yangi buyurtma adminga keladi; holat o'zgarsa mijozga xabar boradi.
- [ ] Admin Mini App ichidan mahsulot (rasm bilan), kategoriya va buyurtmalarni boshqara oladi.
- [ ] Soxta `initData` rad etiladi; oddiy foydalanuvchi admin endpoint'iga kirsa `403`.
- [ ] uz/ru almashadi; savat va buyurtmalar saqlanib qoladi.
- [ ] `docker compose --profile miniapp up -d` bilan HTTPS bilan ishga tushadi.
- [ ] Testlar o'tadi, CI yashil, repoda sirlar yo'q; README + ishlayotgan demo (`@savatcha_app_bot`).

---

# C QISM — v2.1: VEB ADMIN (ixtiyoriy, B qism tugagandan keyin)

Brauzerda (kompyuterda) ochiladigan to'liq admin panel: `https://savatcha.../admin`.
Yangi alohida ilova yozilmaydi: **Mini App dagi (webapp/) admin sahifalari kengaytiriladi** va ikkinchi kirish usuli qo'shiladi. Bir xil API (`/api/admin/*`), bir xil React kod.

## C1. Kirish (brauzer uchun)

**Telegram Login Widget** (parol saqlash yo'q):
1. `/admin` sahifasida "Telegram orqali kirish" tugmasi.
2. Telegram foydalanuvchi ma'lumotini (`id`, `first_name`, `username`, `auth_date`, `hash`) qaytaradi.
3. `POST /api/auth/telegram-login` serverda tekshiradi: `hash` HMAC-SHA256 (`secret = SHA256(BOT_TOKEN_APP)`), `auth_date` 5 daqiqadan eski emas, `id ∈ ADMIN_IDS`. Bo'lmasa `403`.
4. Muvaffaqiyatda **sessiya cookie** beriladi: `HttpOnly`, `Secure`, `SameSite=Strict`, muddati 12 soat; `POST /api/auth/logout` bilan tugatiladi, `GET /api/auth/session` holatni qaytaradi.
5. BotFather da `/setdomain` bilan domen belgilanadi (`@savatcha_app_bot` uchun). Widget faqat shu HTTPS domenda ishlaydi, `localhost` da ishlamaydi: dev uchun Cloudflare Tunnel/ngrok domenini `/setdomain` ga qo'yish kerak.

**Ikki kirish usuli bitta `require_admin` da:** admin endpoint'lari yo `Authorization: tma <initData>` (Mini App ichida) yoki sessiya cookie (brauzerda) bilan ochiladi.

**Xavfsizlik (majburiy):**
- CSRF himoyasi (o'zgartiruvchi so'rovlarda `Origin`/`Referer` tekshiruvi + `SameSite=Strict`).
- Login endpoint'ida rate limit; muvaffaqiyatsiz urinishlar logga yoziladi.
- Sessiya jadvali DB da (`admin_sessions`: token_hash, tg_id, created_at, expires_at, ip, user_agent); token DB da faqat hash ko'rinishida.
- Caddy da xavfsizlik headerlari (`Content-Security-Policy`, `X-Frame-Options`, `Strict-Transport-Security`).
- **Audit log:** har admin amali (`create/update/delete/status_change/login/logout/export`) `audit_log` jadvaliga yoziladi.

## C2. Maket
- Kompyuter (≥1024 px): chap **sidebar** (Dashboard, Buyurtmalar, Mahsulotlar, Kategoriyalar, Mijozlar, Hisobotlar, Audit log, Sozlamalar), yuqorida qidiruv va profil.
- Planshet/telefon: tab bar yoki yig'iladigan menyu (Mini App ichida avvalgidek).
- Yorug/qorong'i tema almashtirgich (brauzerda); Mini App ichida Telegram temasi.
- Yangi buyurtma kelganda **jonli yangilanish** (30 soniyada bir so'rov yoki SSE) va toast xabar.

## C3. Sahifalar va imkoniyatlar

**1) Dashboard**
- Davr filtri: Bugun / 7 kun / 30 kun / Oraliq (sana tanlash).
- KPI kartalar (oldingi davrga nisbatan o'zgarish % bilan): buyurtmalar soni, tushum (daromad), o'rtacha chek, yangi mijozlar, kutilayotgan (yangi) buyurtmalar.
- Grafiklar (Recharts):
  - **Kunlik savdo:** tushum va buyurtma soni (area/line).
  - **Buyurtmalar holati bo'yicha:** donut.
  - **Manba bo'yicha:** Classic bot vs Mini App (donut yoki bar), portfolio uchun qiziq taqqoslash.
  - **Kategoriya bo'yicha tushum:** bar.
  - **Soat bo'yicha buyurtmalar:** qaysi soatda ko'p buyurtma (bar yoki heatmap).
  - **Yangi mijozlar dinamikasi:** kunlar bo'yicha.
- "Eng ko'p sotilgan" qisqa ro'yxat (top 5) va "So'nggi buyurtmalar" (5 ta).

**2) Top mahsulotlar va mahsulot tahlili (Hisobotlar bo'limi)**
- **Top 10 mahsulot:** sotilgan miqdor bo'yicha va tushum bo'yicha (almashtirgich).
- **Sust mahsulotlar:** oxirgi 30 kunda bir marta ham sotilmagan.
- Mahsulot bo'yicha tafsilot: kunlik sotuv grafigi, jami miqdor va tushum.

**3) Buyurtmalar (jadval)**
- Server tomonda sahifalash va saralash; filtrlar: holat, manba (classic/miniapp), sana oralig'i, qidiruv (raqam, ism, telefon).
- Buyurtma tafsiloti yon panelda: mijoz, manzil, tarkib, summa, **chek rasmi ko'rinishi**, holat tarixi.
- Holatni o'zgartirish (bitta yoki **ommaviy**: bir nechta tanlab) → mijozga avtomatik xabar.
- **CSV eksport** (filtrga mos), chop etish uchun qulay buyurtma sahifasi (print CSS).

**4) Mahsulotlar**
- Jadval: rasm, nom, kategoriya, narx, mavjudlik; qidiruv va filtr.
- **Inline tahrir:** narx va mavjudlikni jadvalning o'zida o'zgartirish.
- Qo'shish/tahrirlash formasi (uz/ru, rasm yuklash, rasm ko'rinishi), ommaviy arxivlash.

**5) Kategoriyalar**
- Ro'yxat, qo'shish/tahrirlash, **sudrab tartiblash** (`sort_order`), faol/nofaol.

**6) Mijozlar**
- Jadval: ism, username, telefon, buyurtmalar soni, jami sarflagan, oxirgi buyurtma sanasi, til.
- **Top mijozlar** (sarflagan summa bo'yicha), **takroriy mijozlar ulushi** (2+ buyurtma bergan).
- Mijoz tafsiloti: buyurtmalar tarixi.
- Mijozlar CSV eksporti.

**7) Audit log**
- Kim, qachon, nima qildi (filtr: amal turi, admin, sana). Faqat o'qish.

**8) Sozlamalar**
- Do'kon nomi, aloqa telefoni, ish vaqti (mijozga ko'rsatiladi), xabarnoma sozlamalari (kimga yangi buyurtma xabari borishi). `settings` jadvali (key-value) DB da.
- Chiqish (logout), faol sessiyalar ro'yxati.

**Ixtiyoriy qo'shimchalar (vaqt qolsa):**
- **Ombor (stock):** `products.stock` (nullable) + "kam qoldi" ogohlantirishi; buyurtmada avtomatik kamayadi (core servisida, ikkala interfeys uchun).
- **Promokod / chegirma** (oddiy foiz yoki summa).
- **Kunlik hisobot** adminga botda: har kuni 21:00 da qisqa xulosa (buyurtma soni, tushum, top mahsulot) — rejalashtirilgan vazifa (`APScheduler`).
- **Excel (.xlsx) eksport** (CSV dan tashqari).

## C4. Statistika hisob-kitobi (qoidalar)
- Hamma agregatlar **SQL da** (`core/services/stats.py`); frontend faqat ko'rsatadi. Xuddi shu servis botdagi `/stats` buyrug'ida ham ishlatiladi (qayta ishlatish).
- **Tushum** = `STATS_REVENUE_STATUSES` dagi holatlardagi buyurtmalar summasi (standart: `accepted, delivering, done`; `new` va `cancelled` kirmaydi). "Buyurtmalar soni" KPI si va tushum bir xil holatlar to'plamidan hisoblanadi; `new` buyurtmalar alohida "kutilayotgan" KPI sida ko'rinadi.
- Kunlar chegarasi **Asia/Tashkent** vaqti bo'yicha (UTC emas).
- Bo'sh kunlar grafikda 0 bilan to'ldiriladi (uzilish bo'lmasin).
- Indekslar: `orders(created_at, status)`, `orders(source)`, `order_items(product_id)`.
- Oldingi davr bilan taqqoslash: teng uzunlikdagi oldingi oraliq.

## C5. Qo'shimcha DB o'zgarishlari
```
admin_sessions  id, token_hash, tg_id, created_at, expires_at, ip, user_agent
audit_log       id, admin_tg_id, action, entity, entity_id, details (jsonb), created_at
settings        key (pk), value (jsonb), updated_at
(order_status_history 1.2 da; admin tekshiruvi faqat ADMIN_IDS orqali)
(ixtiyoriy)     products.stock int null, products.low_stock_threshold int null
```

## C6. Qo'shimcha API
| Metod | Yo'l | Tavsif |
|---|---|---|
| POST | `/api/auth/telegram-login` | Widget ma'lumotini tekshirib, sessiya yaratadi |
| POST | `/api/auth/logout` | Sessiyani tugatadi |
| GET | `/api/auth/session` | Joriy sessiya holati |
| GET | `/api/admin/stats/summary?from=&to=` | KPI + oldingi davr bilan taqqoslash |
| GET | `/api/admin/stats/sales-by-day` | Kunlik tushum va buyurtma soni |
| GET | `/api/admin/stats/orders-by-status` | Holat bo'yicha taqsimot |
| GET | `/api/admin/stats/by-source` | Classic vs Mini App |
| GET | `/api/admin/stats/by-category` | Kategoriya bo'yicha tushum |
| GET | `/api/admin/stats/by-hour` | Soat bo'yicha buyurtmalar |
| GET | `/api/admin/stats/top-products?by=qty\|revenue&limit=` | Top mahsulotlar |
| GET | `/api/admin/stats/slow-products?days=30` | Sust mahsulotlar |
| GET | `/api/admin/stats/top-customers?limit=` | Top mijozlar, takroriy ulush |
| GET | `/api/admin/customers` | Mijozlar jadvali (sahifalash, qidiruv, saralash) |
| GET | `/api/admin/orders` | Kengaytirilgan filtrlar (holat, manba, sana, qidiruv, saralash) |
| PATCH | `/api/admin/orders/bulk-status` | Ommaviy holat o'zgartirish |
| GET | `/api/admin/orders/export.csv` | CSV eksport (filtrga mos) |
| GET | `/api/admin/customers/export.csv` | Mijozlar CSV |
| GET | `/api/admin/audit` | Audit log |
| GET / PATCH | `/api/admin/settings` | Sozlamalar |

Hammasi `require_admin` ostida; eksport va o'zgartiruvchi amallar `audit_log` ga yoziladi.

## C7. Bosqichlar (v2.1)

| # | Bosqich | Natija |
|---|---|---|
| C1 | Telegram Login Widget + sessiya cookie + CSRF + rate limit + `require_admin` ikki usulli + testlar | Admin brauzerdan xavfsiz kiradi |
| C2 | Adaptiv admin maketi (sidebar, tema, marshrutlar `/admin/*`) | Kompyuter uchun "qobiq" |
| C3 | `core/services/stats.py` + stats API + testlar (aniq ma'lumot bilan) | To'g'ri raqamlar |
| C4 | Dashboard: KPI kartalar + grafiklar (Recharts) | Dashboard ishlaydi |
| C5 | Hisobotlar: top mahsulotlar, sust mahsulotlar, top mijozlar, soat/kategoriya/manba grafiklari | Tahlil sahifalari |
| C6 | Buyurtmalar jadvali: filtr, saralash, yon panel, ommaviy holat, CSV eksport, print | Kuchli buyurtma boshqaruvi |
| C7 | Mahsulotlar jadvali (inline tahrir), kategoriyalar (sudrab tartiblash), mijozlar sahifasi | To'liq boshqaruv |
| C8 | Audit log + sozlamalar + jonli yangilanish (toast) | Kuzatuv va sozlash |
| C9 | Ixtiyoriy: ombor (stock), kunlik hisobot, xlsx (vaqtga qarab) | Qo'shimchalar |
| C10 | Testlar to'ldirish, CI, Caddy xavfsizlik headerlari, deploy, README (admin skrinshotlari), tag `v2.1-web-admin` | v2.1 portfolioga tayyor |

## C8. Qabul qilish mezonlari (v2.1)
- [ ] Admin brauzerda Telegram orqali kiradi; `ADMIN_IDS` da bo'lmagan foydalanuvchi kira olmaydi (`403`).
- [ ] Soxta yoki eskirgan Telegram login ma'lumoti rad etiladi.
- [ ] Cookie `HttpOnly`/`Secure`/`SameSite=Strict`; logout sessiyani bekor qiladi; CSRF tekshiruvi ishlaydi.
- [ ] Dashboard KPI va grafiklar to'g'ri hisoblangan (test ma'lumotlari bilan tekshirilgan, faqat `STATS_REVENUE_STATUSES` holatlari tushumga kiradi (new va cancelled kirmaydi), kunlar Toshkent vaqtida).
- [ ] Top 10 mahsulot (miqdor va tushum bo'yicha), sust mahsulotlar va top mijozlar ko'rinadi.
- [ ] Buyurtmalar jadvalida filtr, saralash, sahifalash, ommaviy holat o'zgartirish va CSV eksport ishlaydi.
- [ ] Mahsulot narxi/mavjudligi jadvalda to'g'ridan-to'g'ri o'zgartiriladi; kategoriyalar sudrab tartiblanadi.
- [ ] Barcha admin amallari audit logda ko'rinadi.
- [ ] Mini App ichidagi admin ham ishlashda davom etadi (ikki kirish usuli).
- [ ] Testlar o'tadi, CI yashil, repoda sirlar yo'q; README da admin skrinshotlari.

---

## 2. Testlash (umumiy)

**Core / bot (pytest):** savat summasi, buyurtma yaratish (snapshot to'g'ri), bo'sh savat bilan xato, mahsulot arxivlash, telefon validatsiyasi, miqdor chegaralari, boshqa foydalanuvchi savati yopiqligi.
**API (pytest + httpx):** `initData` to'g'ri/noto'g'ri imzo, eskirgan `auth_date`; admin endpoint `403`; fayl yuklash (noto'g'ri tur/hajm rad etiladi); buyurtmada summa serverda hisoblanadi.
**Frontend (vitest, minimal):** narx formatlash, savat hisobi, i18n kalitlari to'liqligi.
**C qism (veb admin):** Telegram login `hash` tekshiruvi (to'g'ri / noto'g'ri / eskirgan / admin bo'lmagan `id`), sessiya cookie bilan `require_admin`, CSRF, `stats` servisi (aniq ma'lumot to'plami → kutilgan summalar, bekor qilingan buyurtmalar tushumga kirmaydi, Toshkent vaqtidagi kun chegarasi, bo'sh kunlar 0), top mahsulotlar tartibi, CSV eksport mazmuni, audit logga yozilishi.
Test DB: SQLite in-memory yoki CI da `postgres` service.

## 3. CI (GitHub Actions)
- Trigger: `push`, `pull_request`.
- Backend: `ruff check` + `ruff format --check` + `pytest` (Postgres service).
- Frontend (v2 dan): `npm ci` → `npm run lint` → `npm test` → `npm run build`.
- README da CI badge.

## 4. Portfolioga joylash
- **Repo:** `savatcha-bot` (tavsif: "Savatcha — Telegram store in two flavours: classic bot (aiogram) and Mini App (React + FastAPI)"; topics: `telegram-bot`, `telegram-mini-app`, `aiogram`, `fastapi`, `react`, `typescript`, `postgresql`, `docker`).
- **README:** ikkala versiya skrinshotlari, arxitektura diagrammasi, **"Classic bot vs Mini App" taqqoslash jadvali** (qaysi mijozga qaysi biri mos), ishga tushirish qadamlari.
- **Demo botlar:** `@savatcha_classic_bot`, `@savatcha_app_bot`.
- **Videolar:** har versiya uchun 30–60 soniya (`/start` → tanlash → savat → buyurtma → admin holatni o'zgartiradi → mijozga xabar).
- **Upwork portfolio:** ikkita alohida element (v1 va v2), har biriga 3–4 skrinshot, 2 gaplik tavsif, GitHub havolasi.
- **Veb admin (v2.1):** v2 elementiga qo'shimcha 3–4 skrinshot (dashboard grafiklari, top mahsulotlar, buyurtmalar jadvali) va 30–60 soniyalik video; README da "Admin panel" bo'limi. Bu "to'liq mahsulot" taassurotini beradi.
- **Narx taklifi (mijozga):** Classic bot — arzonroq, tezroq; Mini App — qimmatroq, mobil ilova tajribasi.

## 5. Claude CLI uchun ko'rsatmalar (CLAUDE.md ga qo'ying)

```
# Savatcha (savatcha-bot)
- Monorepo: src/savatcha/{core,bot,api}, webapp/ (v2). Python 3.12, aiogram 3, FastAPI, SQLAlchemy 2 async, Alembic, PostgreSQL.
- Biznes-mantiq FAQAT core/services da. Handler va routerlar faqat servislarni chaqiradi.
- Pul uchun Decimal. Barcha backend kod async. Type hint majburiy.
- Matnlar faqat locales/*.json (uz, ru); kodda qattiq yozilmasin.
- Admin tekshiruvi filter/Depends orqali. Sirlar faqat .env da.
- Rasm va cheklar diskka saqlanadi (UPLOAD_DIR), DB da yo'l.
- v2: Telegram initData HMAC bilan tekshiriladi, narx va summa faqat serverda hisoblanadi.
- Frontend: TypeScript strict, mobil birinchi, Telegram themeParams/BackButton/MainButton/haptic.
- Admin huquqi faqat ADMIN_IDS orqali (DB da is_admin yo'q). Chek rasmlari receipts/ da, ochiq /files ga kirmaydi. Holat o'zgarishi order_status_history ga yoziladi.
- Veb admin (C qism): statistika faqat core/services/stats.py da, SQL agregat bilan; kunlar Asia/Tashkent; tushum faqat STATS_REVENUE_STATUSES (accepted, delivering, done). Brauzer sessiyasi: HttpOnly Secure SameSite=Strict cookie + CSRF. Har admin amali audit_log ga yoziladi.
- Har o'zgarishdan keyin: `ruff check . && ruff format . && pytest`; frontend: `npm run lint && npm test && npm run build`.
- Kichik qadamlar, har bosqich alohida commit. Bosqich tugaganda qo'lda sinab ko'r.
```

**Birinchi topshiriq (A1) — CLI ga bering:**
> "TZ-telegram-shop-bot.md ni o'qi (loyiha: Savatcha, repo: savatcha-bot). Faqat Yadro va A QISM (v1 classic bot) ustida ishlaymiz. A1 bosqichini bajar: monorepo skeleti (`pyproject.toml`, `src/savatcha/core/config.py`, DB ulanishi, `src/savatcha/bot/main.py`, `docker-compose.yml` (`db`, `bot`), `.env.example`, `.gitignore`), `/start` va til tanlash. Kodni yozishdan oldin reja ber va qaysi fayllarni yaratishingni sana."

**Veb adminni boshlaganda (C1), v2 tugagach:**
> "v2 tugadi (tag v2.0-miniapp). Endi C QISM (veb admin). C1 bosqichini bajar: Telegram Login Widget orqali kirish (`/api/auth/telegram-login`, hash tekshiruvi, ADMIN_IDS), sessiya cookie (HttpOnly, Secure, SameSite=Strict), CSRF himoyasi, login rate limit, `require_admin` ni ikki usulli qil (initData yoki cookie), testlar. Avval reja ber."

**v2 ni boshlaganda (B1):**
> "v1 tugadi (tag v1.0-classic). Endi B QISM (Mini App). B1 bosqichini bajar: `src/savatcha/api/` skeleti, `auth.py` (initData HMAC tekshiruvi), `/api/me`, testlar. Yadro (`core`) dan foydalan, uni nusxalama. Avval reja ber."
