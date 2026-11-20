from aiogram import Bot, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.bot.filters import admin_router
from savatcha.bot.keyboards.admin import (
    AdminCB,
    AdmProdCB,
    archive_confirm_kb,
    choose_cat_for_add_kb,
    product_admin_kb,
    product_cats_kb,
    product_list_kb,
)
from savatcha.bot.states import AdminProductAdd, AdminProductEdit
from savatcha.bot.utils import CAPTION_LIMIT, download_photo, safe_edit, send_product
from savatcha.core.config import get_settings
from savatcha.core.db.models import Product
from savatcha.core.i18n import t
from savatcha.core.services import catalog
from savatcha.core.services.files import PRODUCTS_SUBDIR, ImageError, save_image
from savatcha.core.utils.money import format_price, parse_price

router = admin_router("admin_products")

_TEXT_LIMITS = {"name_uz": 200, "name_ru": 200, "description_uz": 1000, "description_ru": 1000}


def admin_product_text(product: Product, category_name: str, lang: str | None) -> str:
    status = t("in_stock" if product.is_available else "out_of_stock", lang)
    return t(
        "adm_product_card",
        lang,
        id=product.id,
        name_uz=product.name_uz,
        name_ru=product.name_ru,
        desc_uz=product.description_uz or "—",
        desc_ru=product.description_ru or "—",
        price=format_price(product.price),
        category=category_name,
        status=status,
    )[:CAPTION_LIMIT]


async def send_admin_card(
    message: Message, session: AsyncSession, product: Product, lang: str | None
) -> None:
    cat = await catalog.get_category(session, product.category_id)
    text = admin_product_text(product, cat.name_uz if cat else "?", lang)
    await send_product(message, session, product, text, product_admin_kb(product, lang))


async def _list(
    call: CallbackQuery, session: AsyncSession, cat_id: int, page: int, lang: str | None
) -> None:
    cat = await catalog.get_category(session, cat_id)
    if cat is None:
        await call.answer(t("category_gone", lang), show_alert=True)
        return
    await call.answer()
    products, total = await catalog.list_products(
        session, category_id=cat_id, page=page, storefront=False
    )
    await safe_edit(
        call.message,
        t("adm_products_in", lang, name=cat.name_uz, total=total),
        product_list_kb(products, total, cat_id, page, lang),
    )


@router.callback_query(AdminCB.filter(F.act == "products"))
@router.callback_query(AdmProdCB.filter(F.act == "cats"))
async def choose_category(call: CallbackQuery, session: AsyncSession, lang: str | None) -> None:
    await call.answer()
    cats = await catalog.list_categories(session, only_active=False)
    await safe_edit(call.message, t("adm_choose_category", lang), product_cats_kb(cats, lang))


@router.callback_query(AdmProdCB.filter(F.act == "list"))
async def list_in_category(
    call: CallbackQuery, callback_data: AdmProdCB, session: AsyncSession, lang: str | None
) -> None:
    await _list(call, session, callback_data.cat, callback_data.page, lang)


@router.callback_query(AdmProdCB.filter(F.act == "open"))
async def open_product(
    call: CallbackQuery, callback_data: AdmProdCB, session: AsyncSession, lang: str | None
) -> None:
    product = await catalog.get_product(session, callback_data.id)
    if product is None or product.is_archived:
        await call.answer(t("product_gone", lang), show_alert=True)
        return
    await call.answer()
    if isinstance(call.message, Message):
        await send_admin_card(call.message, session, product, lang)


@router.callback_query(AdmProdCB.filter(F.act == "avail"))
async def toggle_avail(
    call: CallbackQuery, callback_data: AdmProdCB, session: AsyncSession, lang: str | None
) -> None:
    product = await catalog.get_product(session, callback_data.id)
    if product is None or product.is_archived:
        await call.answer(t("product_gone", lang), show_alert=True)
        return
    await catalog.toggle_available(session, product)
    await call.answer()
    cat = await catalog.get_category(session, product.category_id)
    await safe_edit(
        call.message,
        admin_product_text(product, cat.name_uz if cat else "?", lang),
        product_admin_kb(product, lang),
    )


@router.callback_query(AdmProdCB.filter(F.act == "arch"))
async def archive_ask(call: CallbackQuery, callback_data: AdmProdCB, lang: str | None) -> None:
    await call.answer()
    await safe_edit(
        call.message, t("confirm_archive", lang), archive_confirm_kb(callback_data.id, lang)
    )


@router.callback_query(AdmProdCB.filter(F.act == "arch_ok"))
async def archive_do(
    call: CallbackQuery, callback_data: AdmProdCB, session: AsyncSession, lang: str | None
) -> None:
    product = await catalog.get_product(session, callback_data.id)
    if product is None:
        await call.answer(t("product_gone", lang), show_alert=True)
        return
    await catalog.archive_product(session, product)
    await call.answer(t("product_archived", lang))
    await safe_edit(call.message, t("product_archived", lang))


# ---- tahrirlash ----
@router.callback_query(AdmProdCB.filter(F.act == "edit"))
async def edit_start(
    call: CallbackQuery,
    callback_data: AdmProdCB,
    state: FSMContext,
    session: AsyncSession,
    lang: str | None,
) -> None:
    product = await catalog.get_product(session, callback_data.id)
    if product is None or product.is_archived:
        await call.answer(t("product_gone", lang), show_alert=True)
        return
    await call.answer()
    await state.set_state(AdminProductEdit.value)
    await state.update_data(product_id=product.id, field=callback_data.f)
    if isinstance(call.message, Message):
        await call.message.answer(t(f"ask_edit_{callback_data.f}", lang))


async def _finish_edit(
    message: Message, state: FSMContext, session: AsyncSession, product: Product, lang: str | None
) -> None:
    await state.clear()
    await message.answer(t("saved", lang))
    await send_admin_card(message, session, product, lang)


@router.message(AdminProductEdit.value, F.photo)
async def edit_photo(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot, lang: str | None
) -> None:
    data = await state.get_data()
    product = await catalog.get_product(session, data["product_id"])
    if product is None:
        await state.clear()
        await message.answer(t("product_gone", lang))
        return
    if data["field"] != "image":
        await message.answer(t("text_needed", lang))
        return
    s = get_settings()
    try:
        path = await save_image(
            await download_photo(bot, message), s.upload_dir, PRODUCTS_SUBDIR, s.max_upload_mb
        )
    except ImageError as exc:
        await message.answer(t(f"image_err_{exc.code}", lang))
        return
    await catalog.update_product(session, product, image_path=path)
    await _finish_edit(message, state, session, product, lang)


@router.message(AdminProductEdit.value, F.text)
async def edit_text(
    message: Message, state: FSMContext, session: AsyncSession, lang: str | None
) -> None:
    data = await state.get_data()
    field, text = data["field"], (message.text or "").strip()
    product = await catalog.get_product(session, data["product_id"])
    if product is None:
        await state.clear()
        await message.answer(t("product_gone", lang))
        return
    if field == "image":
        await message.answer(t("photo_needed", lang))
        return
    if field == "price":
        price = parse_price(text)
        if price is None:
            await message.answer(t("price_invalid", lang))
            return
        await catalog.update_product(session, product, price=price)
    else:
        if not text or len(text) > _TEXT_LIMITS[field]:
            await message.answer(t("text_invalid", lang, limit=_TEXT_LIMITS[field]))
            return
        await catalog.update_product(session, product, **{field: text})
    await _finish_edit(message, state, session, product, lang)


# ---- qo'shish ----
@router.callback_query(AdmProdCB.filter(F.act == "add"))
async def add_start(
    call: CallbackQuery,
    callback_data: AdmProdCB,
    state: FSMContext,
    session: AsyncSession,
    lang: str | None,
) -> None:
    if callback_data.cat == 0:
        await call.answer()
        cats = await catalog.list_categories(session, only_active=False)
        if not cats:
            await call.answer(t("adm_no_categories", lang), show_alert=True)
            return
        await safe_edit(
            call.message, t("adm_choose_category", lang), choose_cat_for_add_kb(cats, lang)
        )
        return
    await call.answer()
    await state.set_state(AdminProductAdd.name_uz)
    await state.update_data(category_id=callback_data.cat)
    if isinstance(call.message, Message):
        await call.message.answer(t("ask_prod_name_uz", lang))


async def _text_step(
    message: Message,
    state: FSMContext,
    lang: str | None,
    key: str,
    next_state,  # noqa: ANN001
    prompt: str,
) -> None:
    text = (message.text or "").strip()
    limit = _TEXT_LIMITS["name_uz" if key.startswith("name") else "description_uz"]
    if not text or len(text) > limit:
        await message.answer(t("text_invalid", lang, limit=limit))
        return
    await state.update_data(**{key: text})
    await state.set_state(next_state)
    await message.answer(t(prompt, lang))


@router.message(AdminProductAdd.name_uz, F.text)
async def add_name_uz(message: Message, state: FSMContext, lang: str | None) -> None:
    await _text_step(message, state, lang, "name_uz", AdminProductAdd.name_ru, "ask_prod_name_ru")


@router.message(AdminProductAdd.name_ru, F.text)
async def add_name_ru(message: Message, state: FSMContext, lang: str | None) -> None:
    await _text_step(message, state, lang, "name_ru", AdminProductAdd.desc_uz, "ask_prod_desc_uz")


@router.message(AdminProductAdd.desc_uz, F.text)
async def add_desc_uz(message: Message, state: FSMContext, lang: str | None) -> None:
    await _text_step(
        message, state, lang, "description_uz", AdminProductAdd.desc_ru, "ask_prod_desc_ru"
    )


@router.message(AdminProductAdd.desc_ru, F.text)
async def add_desc_ru(message: Message, state: FSMContext, lang: str | None) -> None:
    await _text_step(
        message, state, lang, "description_ru", AdminProductAdd.price, "ask_prod_price"
    )


@router.message(AdminProductAdd.price, F.text)
async def add_price(message: Message, state: FSMContext, lang: str | None) -> None:
    price = parse_price(message.text or "")
    if price is None:
        await message.answer(t("price_invalid", lang))
        return
    await state.update_data(price=str(price))
    await state.set_state(AdminProductAdd.photo)
    await message.answer(t("ask_prod_photo", lang))


async def _create(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    lang: str | None,
    image_path: str | None,
) -> None:
    from decimal import Decimal

    d = await state.get_data()
    product = await catalog.create_product(
        session,
        category_id=d["category_id"],
        name_uz=d["name_uz"],
        name_ru=d["name_ru"],
        description_uz=d["description_uz"],
        description_ru=d["description_ru"],
        price=Decimal(d["price"]),
        image_path=image_path,
    )
    await state.clear()
    await message.answer(t("product_added", lang))
    await send_admin_card(message, session, product, lang)


@router.message(AdminProductAdd.photo, F.photo)
async def add_photo(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot, lang: str | None
) -> None:
    s = get_settings()
    try:
        path = await save_image(
            await download_photo(bot, message), s.upload_dir, PRODUCTS_SUBDIR, s.max_upload_mb
        )
    except ImageError as exc:
        await message.answer(t(f"image_err_{exc.code}", lang))
        return
    await _create(message, state, session, lang, path)


@router.message(AdminProductAdd.photo, F.text == "-")
async def add_no_photo(
    message: Message, state: FSMContext, session: AsyncSession, lang: str | None
) -> None:
    await _create(message, state, session, lang, None)


@router.message(AdminProductAdd.photo)
async def add_photo_wrong(message: Message, lang: str | None) -> None:
    await message.answer(t("photo_needed", lang))
