from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.api.deps import get_session, require_admin, settings_dep
from savatcha.api.schemas import ProductOut, ProductPage, product_out
from savatcha.api.uploads import store_upload
from savatcha.core.config import Settings
from savatcha.core.services import catalog
from savatcha.core.services.files import PRODUCTS_SUBDIR
from savatcha.core.utils.money import parse_price

router = APIRouter(prefix="/products", dependencies=[Depends(require_admin)])


def _price(raw: str) -> Decimal:
    value = parse_price(raw)
    if value is None:
        raise HTTPException(422, "invalid_price")
    return value


async def _get(session: AsyncSession, product_id: int):
    p = await catalog.get_product(session, product_id)
    if p is None or p.is_archived:
        raise HTTPException(404, "not_found")
    return p


async def _check_category(session: AsyncSession, category_id: int) -> None:
    if await catalog.get_category(session, category_id) is None:
        raise HTTPException(422, "invalid_category")


@router.get("", response_model=ProductPage)
async def list_products(
    category: int | None = None,
    q: str | None = Query(default=None, max_length=50),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    items, total = await catalog.list_products(
        session, category_id=category, query=q, page=page, per_page=per_page, storefront=False
    )
    return ProductPage(
        items=[product_out(p) for p in items],
        total=total,
        page=page,
        pages=max(1, -(-total // per_page)),
    )


@router.post("", response_model=ProductOut, status_code=201)
async def create(
    category_id: int = Form(),
    name_uz: str = Form(min_length=1, max_length=200),
    name_ru: str = Form(min_length=1, max_length=200),
    description_uz: str = Form(default="", max_length=1000),
    description_ru: str = Form(default="", max_length=1000),
    price: str = Form(),
    is_available: bool = Form(default=True),
    image: UploadFile | None = File(default=None),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_dep),
):
    await _check_category(session, category_id)
    price_value = _price(price)
    image_path = None
    if image is not None and image.filename:
        image_path = await store_upload(image, settings, PRODUCTS_SUBDIR)
    p = await catalog.create_product(
        session,
        category_id=category_id,
        name_uz=name_uz,
        name_ru=name_ru,
        description_uz=description_uz,
        description_ru=description_ru,
        price=price_value,
        image_path=image_path,
    )
    if not is_available:
        await catalog.toggle_available(session, p)
    return product_out(p)


@router.patch("/{product_id}", response_model=ProductOut)
async def update(
    product_id: int,
    category_id: int | None = Form(default=None),
    name_uz: str | None = Form(default=None, min_length=1, max_length=200),
    name_ru: str | None = Form(default=None, min_length=1, max_length=200),
    description_uz: str | None = Form(default=None, max_length=1000),
    description_ru: str | None = Form(default=None, max_length=1000),
    price: str | None = Form(default=None),
    is_available: bool | None = Form(default=None),
    image: UploadFile | None = File(default=None),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_dep),
):
    p = await _get(session, product_id)
    fields: dict[str, object] = {}
    if category_id is not None:
        await _check_category(session, category_id)
        fields["category_id"] = category_id
    for key, value in (
        ("name_uz", name_uz),
        ("name_ru", name_ru),
        ("description_uz", description_uz),
        ("description_ru", description_ru),
    ):
        if value is not None:
            fields[key] = value
    if price is not None:
        fields["price"] = _price(price)
    if image is not None and image.filename:
        fields["image_path"] = await store_upload(image, settings, PRODUCTS_SUBDIR)
    if fields:
        await catalog.update_product(session, p, **fields)
    if is_available is not None and is_available != p.is_available:
        await catalog.toggle_available(session, p)
    return product_out(p)


@router.delete("/{product_id}", status_code=204)
async def archive(
    product_id: int,
    session: AsyncSession = Depends(get_session),
):
    await catalog.archive_product(session, await _get(session, product_id))
