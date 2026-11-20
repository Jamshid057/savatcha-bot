from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.api.deps import get_session, require_admin
from savatcha.api.schemas import CategoryIn, CategoryOut, CategoryPatch, ReorderIn
from savatcha.core.db.models import User
from savatcha.core.services import audit, catalog

router = APIRouter(prefix="/categories")


async def _get(session: AsyncSession, category_id: int):
    cat = await catalog.get_category(session, category_id)
    if cat is None:
        raise HTTPException(404, "not_found")
    return cat


@router.get("", response_model=list[CategoryOut])
async def list_categories(
    _: User = Depends(require_admin), session: AsyncSession = Depends(get_session)
):
    return await catalog.list_categories(session, only_active=False)


@router.post("", response_model=CategoryOut, status_code=201)
async def create(
    body: CategoryIn,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    cat = await catalog.create_category(session, body.name_uz, body.name_ru)
    if not body.is_active:
        await catalog.set_category_active(session, cat, False)
    await audit.log_action(
        session, admin.tg_id, "create", "category", cat.id, {"name": cat.name_uz}
    )
    return cat


@router.patch("/reorder", status_code=204)
async def reorder(
    body: ReorderIn,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    try:
        await catalog.reorder_categories(session, body.ids)
    except catalog.CatalogError as exc:
        raise HTTPException(422, "invalid_order") from exc
    await audit.log_action(session, admin.tg_id, "update", "category", None, {"reorder": body.ids})


@router.patch("/{category_id}", response_model=CategoryOut)
async def update(
    category_id: int,
    body: CategoryPatch,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    cat = await _get(session, category_id)
    await catalog.rename_category(
        session, cat, body.name_uz or cat.name_uz, body.name_ru or cat.name_ru
    )
    if body.is_active is not None:
        await catalog.set_category_active(session, cat, body.is_active)
    await audit.log_action(
        session, admin.tg_id, "update", "category", cat.id, body.model_dump(exclude_none=True)
    )
    return cat


@router.delete("/{category_id}", status_code=204)
async def delete(
    category_id: int,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    cat = await _get(session, category_id)
    try:
        await catalog.delete_category(session, cat)
    except catalog.CategoryNotEmpty as exc:
        raise HTTPException(409, "category_not_empty") from exc
    await audit.log_action(session, admin.tg_id, "delete", "category", category_id)
