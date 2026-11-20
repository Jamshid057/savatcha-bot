from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.api.deps import get_session, require_admin
from savatcha.api.schemas import CategoryIn, CategoryOut, CategoryPatch
from savatcha.core.services import catalog

router = APIRouter(prefix="/categories", dependencies=[Depends(require_admin)])


async def _get(session: AsyncSession, category_id: int):
    cat = await catalog.get_category(session, category_id)
    if cat is None:
        raise HTTPException(404, "not_found")
    return cat


@router.get("", response_model=list[CategoryOut])
async def list_categories(session: AsyncSession = Depends(get_session)):
    return await catalog.list_categories(session, only_active=False)


@router.post("", response_model=CategoryOut, status_code=201)
async def create(body: CategoryIn, session: AsyncSession = Depends(get_session)):
    cat = await catalog.create_category(session, body.name_uz, body.name_ru)
    if not body.is_active:
        await catalog.set_category_active(session, cat, False)
    return cat


@router.patch("/{category_id}", response_model=CategoryOut)
async def update(
    category_id: int, body: CategoryPatch, session: AsyncSession = Depends(get_session)
):
    cat = await _get(session, category_id)
    await catalog.rename_category(
        session, cat, body.name_uz or cat.name_uz, body.name_ru or cat.name_ru
    )
    if body.is_active is not None:
        await catalog.set_category_active(session, cat, body.is_active)
    return cat


@router.delete("/{category_id}", status_code=204)
async def delete(category_id: int, session: AsyncSession = Depends(get_session)):
    cat = await _get(session, category_id)
    try:
        await catalog.delete_category(session, cat)
    except catalog.CategoryNotEmpty as exc:
        raise HTTPException(409, "category_not_empty") from exc
