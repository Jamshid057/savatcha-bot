from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.bot.filters import admin_router
from savatcha.bot.keyboards.admin import (
    AdmCatCB,
    AdminCB,
    categories_admin_kb,
    category_delete_confirm_kb,
    category_kb,
)
from savatcha.bot.states import AdminCategoryAdd, AdminCategoryRename
from savatcha.bot.utils import safe_edit
from savatcha.core.i18n import t
from savatcha.core.services import catalog

router = admin_router("admin_categories")


async def _show_list(call: CallbackQuery, session: AsyncSession, lang: str | None) -> None:
    cats = await catalog.list_categories(session, only_active=False)
    await safe_edit(call.message, t("adm_categories_title", lang), categories_admin_kb(cats, lang))


@router.callback_query(AdminCB.filter(F.act == "categories"))
async def open_list(call: CallbackQuery, session: AsyncSession, lang: str | None) -> None:
    await call.answer()
    await _show_list(call, session, lang)


@router.callback_query(AdmCatCB.filter(F.act == "list"))
async def back_list(call: CallbackQuery, session: AsyncSession, lang: str | None) -> None:
    await call.answer()
    await _show_list(call, session, lang)


@router.callback_query(AdmCatCB.filter(F.act == "open"))
async def open_category(
    call: CallbackQuery, callback_data: AdmCatCB, session: AsyncSession, lang: str | None
) -> None:
    cat = await catalog.get_category(session, callback_data.id)
    if cat is None:
        await call.answer(t("category_gone", lang), show_alert=True)
        return
    await call.answer()
    status = t("cat_active" if cat.is_active else "cat_inactive", lang)
    await safe_edit(
        call.message,
        t("adm_category_card", lang, uz=cat.name_uz, ru=cat.name_ru, status=status),
        category_kb(cat, lang),
    )


# ---- qo'shish ----
@router.callback_query(AdmCatCB.filter(F.act == "add"))
async def add_start(call: CallbackQuery, state: FSMContext, lang: str | None) -> None:
    await call.answer()
    await state.set_state(AdminCategoryAdd.name_uz)
    if isinstance(call.message, Message):
        await call.message.answer(t("ask_cat_name_uz", lang))


@router.message(AdminCategoryAdd.name_uz, F.text)
async def add_name_uz(message: Message, state: FSMContext, lang: str | None) -> None:
    await state.update_data(name_uz=(message.text or "").strip()[:100])
    await state.set_state(AdminCategoryAdd.name_ru)
    await message.answer(t("ask_cat_name_ru", lang))


@router.message(AdminCategoryAdd.name_ru, F.text)
async def add_name_ru(
    message: Message, state: FSMContext, session: AsyncSession, lang: str | None
) -> None:
    data = await state.get_data()
    await state.clear()
    cat = await catalog.create_category(
        session, data["name_uz"], (message.text or "").strip()[:100]
    )
    await message.answer(
        t("category_added", lang, name=cat.name_uz),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=categories_admin_kb(
                await catalog.list_categories(session, only_active=False), lang
            ).inline_keyboard
        ),
    )


# ---- nomini o'zgartirish ----
@router.callback_query(AdmCatCB.filter(F.act == "rename"))
async def rename_start(
    call: CallbackQuery, callback_data: AdmCatCB, state: FSMContext, lang: str | None
) -> None:
    await call.answer()
    await state.set_state(AdminCategoryRename.name_uz)
    await state.update_data(cat_id=callback_data.id)
    if isinstance(call.message, Message):
        await call.message.answer(t("ask_cat_name_uz", lang))


@router.message(AdminCategoryRename.name_uz, F.text)
async def rename_name_uz(message: Message, state: FSMContext, lang: str | None) -> None:
    await state.update_data(name_uz=(message.text or "").strip()[:100])
    await state.set_state(AdminCategoryRename.name_ru)
    await message.answer(t("ask_cat_name_ru", lang))


@router.message(AdminCategoryRename.name_ru, F.text)
async def rename_name_ru(
    message: Message, state: FSMContext, session: AsyncSession, lang: str | None
) -> None:
    data = await state.get_data()
    await state.clear()
    cat = await catalog.get_category(session, data["cat_id"])
    if cat is None:
        await message.answer(t("category_gone", lang))
        return
    await catalog.rename_category(session, cat, data["name_uz"], (message.text or "").strip()[:100])
    status = t("cat_active" if cat.is_active else "cat_inactive", lang)
    await message.answer(
        t("adm_category_card", lang, uz=cat.name_uz, ru=cat.name_ru, status=status),
        reply_markup=category_kb(cat, lang),
    )


# ---- faol/nofaol, o'chirish ----
@router.callback_query(AdmCatCB.filter(F.act == "toggle"))
async def toggle(
    call: CallbackQuery, callback_data: AdmCatCB, session: AsyncSession, lang: str | None
) -> None:
    cat = await catalog.get_category(session, callback_data.id)
    if cat is None:
        await call.answer(t("category_gone", lang), show_alert=True)
        return
    await call.answer()
    await catalog.set_category_active(session, cat, not cat.is_active)
    status = t("cat_active" if cat.is_active else "cat_inactive", lang)
    await safe_edit(
        call.message,
        t("adm_category_card", lang, uz=cat.name_uz, ru=cat.name_ru, status=status),
        category_kb(cat, lang),
    )


@router.callback_query(AdmCatCB.filter(F.act == "del"))
async def delete_ask(call: CallbackQuery, callback_data: AdmCatCB, lang: str | None) -> None:
    await call.answer()
    await safe_edit(
        call.message,
        t("confirm_delete_category", lang),
        category_delete_confirm_kb(callback_data.id, lang),
    )


@router.callback_query(AdmCatCB.filter(F.act == "del_ok"))
async def delete_do(
    call: CallbackQuery, callback_data: AdmCatCB, session: AsyncSession, lang: str | None
) -> None:
    cat = await catalog.get_category(session, callback_data.id)
    if cat is None:
        await call.answer(t("category_gone", lang), show_alert=True)
        return
    try:
        await catalog.delete_category(session, cat)
    except catalog.CategoryNotEmpty:
        await call.answer(t("category_not_empty", lang), show_alert=True)
        status = t("cat_active" if cat.is_active else "cat_inactive", lang)
        await safe_edit(
            call.message,
            t("adm_category_card", lang, uz=cat.name_uz, ru=cat.name_ru, status=status),
            category_kb(cat, lang),
        )
        return
    await call.answer(t("category_deleted", lang))
    await _show_list(call, session, lang)
