from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.bot.filters import admin_router
from savatcha.bot.keyboards.admin import AdminCB, admin_menu_kb, back_to_admin
from savatcha.bot.utils import safe_edit
from savatcha.core.config import get_settings
from savatcha.core.i18n import t
from savatcha.core.services import stats
from savatcha.core.utils.money import format_price

router: Router = admin_router("admin_panel")


async def stats_text(session: AsyncSession, lang: str | None) -> str:
    data = await stats.today_and_week(session, get_settings().stats_revenue_statuses)
    (tn, ts), (wn, ws) = data["today"], data["week"]
    return t(
        "stats_text",
        lang,
        today_n=tn,
        today_sum=format_price(ts, lang),
        week_n=wn,
        week_sum=format_price(ws, lang),
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext, lang: str | None) -> None:
    await state.clear()
    await message.answer(t("admin_title", lang), reply_markup=admin_menu_kb(lang))


@router.message(Command("stats"))
async def cmd_stats(
    message: Message, state: FSMContext, session: AsyncSession, lang: str | None
) -> None:
    await state.clear()
    await message.answer(await stats_text(session, lang))


@router.callback_query(AdminCB.filter(F.act == "menu"))
async def menu(call: CallbackQuery, state: FSMContext, lang: str | None) -> None:
    await call.answer()
    await state.clear()
    await safe_edit(call.message, t("admin_title", lang), admin_menu_kb(lang))


@router.callback_query(AdminCB.filter(F.act == "stats"))
async def stats_cb(call: CallbackQuery, session: AsyncSession, lang: str | None) -> None:
    await call.answer()
    await safe_edit(
        call.message,
        await stats_text(session, lang),
        InlineKeyboardMarkup(inline_keyboard=[back_to_admin(lang)]),
    )
