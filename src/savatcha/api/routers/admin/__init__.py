from fastapi import APIRouter

from savatcha.api.routers.admin import (
    audit,
    categories,
    customers,
    orders,
    products,
    settings,
    stats,
)

router = APIRouter(prefix="/admin", tags=["admin"])
for module in (categories, products, orders, stats, customers, audit, settings):
    router.include_router(module.router)
