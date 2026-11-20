from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.api.deps import current_user, get_session, settings_dep
from savatcha.core.config import Settings
from savatcha.core.services import shop_settings

router = APIRouter(tags=["shop"], dependencies=[Depends(current_user)])


@router.get("/shop")
async def shop_info(
    session: AsyncSession = Depends(get_session), settings: Settings = Depends(settings_dep)
):
    """Mijozga ko'rsatiladigan do'kon ma'lumoti (admin sozlamalaridan)."""
    values = await shop_settings.get_all(session, settings)
    return {k: values[k] for k in ("shop_name", "shop_phone", "work_hours")}
