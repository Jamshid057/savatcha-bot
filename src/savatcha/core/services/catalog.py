from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.core.db.models import Category, Product

PAGE_SIZE = 5
_EDITABLE = {
    "name_uz",
    "name_ru",
    "description_uz",
    "description_ru",
    "price",
    "category_id",
    "image_path",
}


class CatalogError(Exception):
    pass


class CategoryNotEmpty(CatalogError):
    pass


def localized(obj: Category | Product, field: str, lang: str | None) -> str:
    """`name` / `description` maydonini tilga qarab qaytaradi."""
    return getattr(obj, f"{field}_{'ru' if lang == 'ru' else 'uz'}")


# ---- kategoriyalar ----
async def list_categories(session: AsyncSession, *, only_active: bool = True) -> list[Category]:
    stmt = select(Category).order_by(Category.sort_order, Category.id)
    if only_active:
        stmt = stmt.where(Category.is_active.is_(True))
    return list((await session.scalars(stmt)).all())


async def get_category(session: AsyncSession, category_id: int) -> Category | None:
    return await session.get(Category, category_id)


async def create_category(session: AsyncSession, name_uz: str, name_ru: str) -> Category:
    last = await session.scalar(select(func.max(Category.sort_order)))
    cat = Category(name_uz=name_uz, name_ru=name_ru, sort_order=(last or 0) + 1)
    session.add(cat)
    await session.commit()
    return cat


async def rename_category(
    session: AsyncSession, category: Category, name_uz: str, name_ru: str
) -> None:
    category.name_uz, category.name_ru = name_uz, name_ru
    await session.commit()


async def set_category_active(session: AsyncSession, category: Category, active: bool) -> None:
    category.is_active = active
    await session.commit()


async def delete_category(session: AsyncSession, category: Category) -> None:
    """Ichida mahsulot (arxivlangani ham) bo'lsa CategoryNotEmpty."""
    count = await session.scalar(
        select(func.count()).select_from(Product).where(Product.category_id == category.id)
    )
    if count:
        raise CategoryNotEmpty
    await session.delete(category)
    await session.commit()


# ---- mahsulotlar ----
def _like_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def list_products(
    session: AsyncSession,
    *,
    category_id: int | None = None,
    query: str | None = None,
    page: int = 1,
    per_page: int = PAGE_SIZE,
    storefront: bool = True,
) -> tuple[list[Product], int]:
    """(sahifadagi mahsulotlar, jami soni). `storefront=True` — mijoz ko'rinishi (faol kategoriya)."""
    conds = [Product.is_archived.is_(False)]
    if category_id is not None:
        conds.append(Product.category_id == category_id)
    if query:
        pattern = f"%{_like_escape(query.strip())}%"
        conds.append(
            Product.name_uz.ilike(pattern, escape="\\")
            | Product.name_ru.ilike(pattern, escape="\\")
        )
    base = select(Product).where(*conds)
    if storefront:
        base = base.join(Category).where(Category.is_active.is_(True))
    total = await session.scalar(select(func.count()).select_from(base.subquery())) or 0
    page = max(1, page)
    stmt = base.order_by(Product.id).limit(per_page).offset((page - 1) * per_page)
    return list((await session.scalars(stmt)).all()), total


async def get_product(session: AsyncSession, product_id: int) -> Product | None:
    return await session.get(Product, product_id)


def _validate_price(price: Decimal) -> None:
    if price <= 0:
        raise CatalogError("price must be positive")


async def create_product(
    session: AsyncSession,
    *,
    category_id: int,
    name_uz: str,
    name_ru: str,
    description_uz: str,
    description_ru: str,
    price: Decimal,
    image_path: str | None,
) -> Product:
    _validate_price(price)
    product = Product(
        category_id=category_id,
        name_uz=name_uz,
        name_ru=name_ru,
        description_uz=description_uz,
        description_ru=description_ru,
        price=price,
        image_path=image_path,
    )
    session.add(product)
    await session.commit()
    return product


async def update_product(session: AsyncSession, product: Product, **fields: object) -> None:
    unknown = set(fields) - _EDITABLE
    if unknown:
        raise CatalogError(f"not editable: {sorted(unknown)}")
    if "price" in fields:
        _validate_price(fields["price"])  # type: ignore[arg-type]
    if "image_path" in fields:
        product.tg_file_id = None  # eski rasmning kesh id si yaroqsiz
    for key, value in fields.items():
        setattr(product, key, value)
    await session.commit()


async def set_tg_file_id(session: AsyncSession, product: Product, file_id: str) -> None:
    product.tg_file_id = file_id
    await session.commit()


async def toggle_available(session: AsyncSession, product: Product) -> bool:
    product.is_available = not product.is_available
    await session.commit()
    return product.is_available


async def archive_product(session: AsyncSession, product: Product) -> None:
    product.is_archived = True
    product.is_available = False
    await session.commit()
