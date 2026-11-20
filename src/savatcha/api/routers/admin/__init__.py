from fastapi import APIRouter

from savatcha.api.routers.admin import categories, orders, products

router = APIRouter(prefix="/admin", tags=["admin"])
for module in (categories, products, orders):
    router.include_router(module.router)
