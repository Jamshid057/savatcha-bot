from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.api.deps import current_user, get_session
from savatcha.api.schemas import CategoryOut, ProductOut, ProductPage, product_out
from savatcha.core.services import catalog

router = APIRouter(tags=["catalog"], dependencies=[Depends(current_user)])


@router.get("/categories", response_model=list[CategoryOut])
async def categories(session: AsyncSession = Depends(get_session)):
    return await catalog.list_categories(session)


@router.get("/products", response_model=ProductPage)
async def products(
    category: int | None = None,
    q: str | None = Query(default=None, max_length=50),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
):
    items, total = await catalog.list_products(
        session, category_id=category, query=q, page=page, per_page=per_page
    )
    return ProductPage(
        items=[product_out(p) for p in items],
        total=total,
        page=page,
        pages=max(1, -(-total // per_page)),
    )


@router.get("/products/{product_id}", response_model=ProductOut)
async def product(product_id: int, session: AsyncSession = Depends(get_session)):
    p = await catalog.get_product(session, product_id)
    if p is None or p.is_archived:
        raise HTTPException(404, "not_found")
    return product_out(p)
