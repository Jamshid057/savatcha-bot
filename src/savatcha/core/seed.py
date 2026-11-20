"""Demo ma'lumotlar: `python -m savatcha.core.seed`. Qayta ishga tushirish xavfsiz (idempotent)."""

import asyncio
import colorsys
import logging
from decimal import Decimal

from PIL import Image, ImageDraw
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.core.config import get_settings
from savatcha.core.db.base import make_engine, make_session_factory
from savatcha.core.db.models import Category, Product
from savatcha.core.services.files import PRODUCTS_SUBDIR, new_image_name, upload_path

log = logging.getLogger(__name__)

# (nom_uz, nom_ru, [(nom_uz, nom_ru, tavsif_uz, tavsif_ru, narx)])
CATALOG = [
    (
        "Ichimliklar",
        "Напитки",
        [
            (
                "Coca-Cola 1.5L",
                "Coca-Cola 1.5л",
                "Gazlangan ichimlik",
                "Газированный напиток",
                12000,
            ),
            ("Mineral suv 1L", "Минеральная вода 1л", "Gazsiz suv", "Негазированная вода", 5000),
            (
                "Apelsin sharbati",
                "Апельсиновый сок",
                "Tabiiy sharbat, 1L",
                "Натуральный сок, 1л",
                18000,
            ),
            ("Ko'k choy", "Зелёный чай", "Qadoqlangan, 100 g", "Упаковка 100 г", 15000),
        ],
    ),
    (
        "Non va qandolat",
        "Выпечка",
        [
            ("Patir non", "Патыр", "Tandirda pishgan", "Из тандыра", 6000),
            ("Napoleon torti", "Торт Наполеон", "Yangi, 1 kg", "Свежий, 1 кг", 95000),
            ("Kruassan", "Круассан", "Saryog'li", "Сливочный", 9000),
            ("Shokoladli pechenye", "Шоколадное печенье", "300 g", "300 г", 14000),
        ],
    ),
    (
        "Sut mahsulotlari",
        "Молочные продукты",
        [
            ("Sut 1L", "Молоко 1л", "3.2% yog'lilik", "Жирность 3.2%", 11000),
            ("Qatiq 500 g", "Катык 500 г", "Tabiiy qatiq", "Натуральный катык", 9000),
            ("Pishloq", "Сыр", "Rossiya pishlog'i, 200 g", "Российский сыр, 200 г", 28000),
            ("Tvorog", "Творог", "Yangi, 400 g", "Свежий, 400 г", 16000),
        ],
    ),
    (
        "Mevalar",
        "Фрукты",
        [
            ("Olma 1 kg", "Яблоки 1 кг", "Mahalliy", "Местные", 14000),
            ("Banan 1 kg", "Бананы 1 кг", "Import", "Импортные", 22000),
            ("Uzum 1 kg", "Виноград 1 кг", "Shirin, urug'siz", "Сладкий, без косточек", 30000),
            ("Anor 1 kg", "Гранат 1 кг", "Kattaqo'rg'on", "Каттакурган", 25000),
        ],
    ),
    (
        "Uy-ro'zg'or",
        "Для дома",
        [
            ("Kir yuvish kukuni", "Стиральный порошок", "3 kg", "3 кг", 55000),
            ("Idish yuvish suyuqligi", "Средство для посуды", "500 ml", "500 мл", 13000),
            ("Qog'oz sochiq", "Бумажные полотенца", "2 dona", "2 шт.", 12000),
        ],
    ),
]


def _make_image(text: str, hue: float, dest_dir: str) -> str:
    """Rangli joy egallovchi rasm; DB ga `products/<nom>` yo'li yoziladi."""
    r, g, b = (int(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.35, 0.95))
    img = Image.new("RGB", (600, 600), (r, g, b))
    draw = ImageDraw.Draw(img)
    draw.text((30, 280), text[:28], fill=(40, 40, 40))
    name = new_image_name()
    path = upload_path(dest_dir, PRODUCTS_SUBDIR, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "JPEG", quality=80, optimize=True)
    return f"{PRODUCTS_SUBDIR}/{name}"


async def seed(session: AsyncSession, upload_dir: str) -> bool:
    if await session.scalar(select(func.count()).select_from(Category)):
        log.info("Ma'lumotlar bor, seed o'tkazib yuborildi")
        return False
    for order, (cat_uz, cat_ru, products) in enumerate(CATALOG):
        cat = Category(name_uz=cat_uz, name_ru=cat_ru, sort_order=order)
        session.add(cat)
        await session.flush()
        for i, (n_uz, n_ru, d_uz, d_ru, price) in enumerate(products):
            hue = (order * 0.19 + i * 0.04) % 1.0
            session.add(
                Product(
                    category_id=cat.id,
                    name_uz=n_uz,
                    name_ru=n_ru,
                    description_uz=d_uz,
                    description_ru=d_ru,
                    price=Decimal(price),
                    image_path=_make_image(n_uz, hue, upload_dir),
                    # Namuna: oxirgi mahsulot "tugagan" holatda
                    is_available=not (order == 2 and i == 3),
                )
            )
    await session.commit()
    return True


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    engine = make_engine(settings.database_url)
    async with make_session_factory(engine)() as session:
        created = await seed(session, settings.upload_dir)
    await engine.dispose()
    log.info("Seed: %s", "yaratildi" if created else "o'tkazildi")


if __name__ == "__main__":
    asyncio.run(main())
