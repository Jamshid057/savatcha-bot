from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.api.deps import get_session, require_admin, settings_dep
from savatcha.api.periods import parse_period
from savatcha.core.config import Settings
from savatcha.core.services import catalog, stats

router = APIRouter(prefix="/stats", dependencies=[Depends(require_admin)])

Period = tuple[date, date]


@router.get("/summary")
async def summary(
    period: Period = Depends(parse_period),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_dep),
):
    return await stats.summary(session, *period, settings.stats_revenue_statuses)


@router.get("/sales-by-day")
async def sales_by_day(
    period: Period = Depends(parse_period),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_dep),
):
    return await stats.sales_by_day(session, *period, settings.stats_revenue_statuses)


@router.get("/orders-by-status")
async def orders_by_status(
    period: Period = Depends(parse_period), session: AsyncSession = Depends(get_session)
):
    return await stats.orders_by_status(session, *period)


@router.get("/by-source")
async def by_source(
    period: Period = Depends(parse_period),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_dep),
):
    return await stats.by_source(session, *period, settings.stats_revenue_statuses)


@router.get("/by-category")
async def by_category(
    period: Period = Depends(parse_period),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_dep),
):
    return await stats.by_category(session, *period, settings.stats_revenue_statuses)


@router.get("/by-hour")
async def by_hour(
    period: Period = Depends(parse_period),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_dep),
):
    return await stats.by_hour(session, *period, settings.stats_revenue_statuses)


@router.get("/new-customers")
async def new_customers(
    period: Period = Depends(parse_period), session: AsyncSession = Depends(get_session)
):
    return await stats.new_customers_by_day(session, *period)


@router.get("/top-products")
async def top_products(
    by: str = Query(default="qty", pattern="^(qty|revenue)$"),
    limit: int = Query(default=10, ge=1, le=50),
    all_time: bool = False,
    period: Period = Depends(parse_period),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_dep),
):
    d_from, d_to = (None, None) if all_time else period
    return await stats.top_products(
        session, settings.stats_revenue_statuses, by=by, limit=limit, d_from=d_from, d_to=d_to
    )


@router.get("/slow-products")
async def slow_products(
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_dep),
):
    return await stats.slow_products(session, settings.stats_revenue_statuses, days=days)


@router.get("/product/{product_id}")
async def product_detail(
    product_id: int,
    period: Period = Depends(parse_period),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_dep),
):
    product = await catalog.get_product(session, product_id)
    if product is None:
        raise HTTPException(404, "not_found")
    data = await stats.product_detail(session, product_id, *period, settings.stats_revenue_statuses)
    return {**data, "name_uz": product.name_uz, "name_ru": product.name_ru}


@router.get("/top-customers")
async def top_customers(
    limit: int = Query(default=10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_dep),
):
    return await stats.top_customers(session, settings.stats_revenue_statuses, limit=limit)
