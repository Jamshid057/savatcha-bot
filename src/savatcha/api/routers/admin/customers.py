from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.api.deps import get_session, require_admin, settings_dep
from savatcha.api.schemas import CustomerOut, CustomerPage, order_out
from savatcha.core.config import Settings
from savatcha.core.db.models import User
from savatcha.core.services import audit, csv_export, customers
from savatcha.core.services import orders as order_service

router = APIRouter(prefix="/customers")


def _out(row: customers.CustomerRow) -> CustomerOut:
    u = row.user
    return CustomerOut(
        id=u.id,
        tg_id=u.tg_id,
        full_name=u.full_name,
        username=u.username,
        phone=u.phone,
        lang=u.lang,
        created_at=u.created_at,
        orders_count=row.orders_count,
        total_spent=row.total_spent,
        last_order_at=row.last_order_at,
    )


@router.get("", response_model=CustomerPage)
async def list_customers(
    search: str | None = Query(default=None, max_length=100),
    sort: str = "created_at",
    dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_dep),
):
    rows, total = await customers.list_customers(
        session,
        settings.stats_revenue_statuses,
        search=search,
        sort=sort,
        direction=dir,
        page=page,
        per_page=per_page,
    )
    return CustomerPage(
        items=[_out(r) for r in rows], total=total, page=page, pages=max(1, -(-total // per_page))
    )


@router.get("/export.csv")
async def export_csv(
    search: str | None = Query(default=None, max_length=100),
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_dep),
):
    rows, _ = await customers.list_customers(
        session, settings.stats_revenue_statuses, search=search, per_page=10_000
    )
    await audit.log_action(session, admin.tg_id, "export", "customer", None, {"rows": len(rows)})
    return Response(
        csv_export.customers_csv(rows),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="customers.csv"'},
    )


@router.get("/{user_id}")
async def customer_detail(
    user_id: int,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(settings_dep),
):
    row = await customers.get_customer(session, user_id, settings.stats_revenue_statuses)
    if row is None:
        raise HTTPException(404, "not_found")
    orders = await order_service.list_user_orders(session, user_id, limit=100)
    return {
        "customer": _out(row).model_dump(mode="json"),
        "orders": [order_out(o).model_dump(mode="json") for o in orders],
    }
