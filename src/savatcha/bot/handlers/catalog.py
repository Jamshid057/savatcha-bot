from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.bot.keyboards.catalog import (
    AddCB,
    CatCB,
    ProdCB,
    QtyCB,
    SearchPageCB,
    categories_kb,
    product_card_kb,
    products_kb,
)
from savatcha.bot.keyboards.common import MenuCB
from savatcha.bot.states import SearchStates
from savatcha.bot.utils import product_text, safe_edit, send_product
from savatcha.core.db.models import User
from savatcha.core.i18n import t
from savatcha.core.services import cart as cart_service
from savatcha.core.services import catalog
from savatcha.core.services.catalog import localized

router = Router(name="catalog")


async def show_categories(message: Message, session: AsyncSession, lang: str | None) -> None:
    cats = await catalog.list_categories(session)
    if not cats:
        await message.answer(t("catalog_empty", lang))
        return
    await message.answer(t("choose_category", lang), reply_markup=categories_kb(cats, lang))


@router.callback_query(MenuCB.filter(F.act == "noop"))
async def noop(call: CallbackQuery) -> None:
    await call.answer()


@router.callback_query(MenuCB.filter(F.act == "cats"))
async def back_to_categories(call: CallbackQuery, session: AsyncSession, lang: str | None) -> None:
    await call.answer()
    cats = await catalog.list_categories(session)
    if cats:
        await safe_edit(call.message, t("choose_category", lang), categories_kb(cats, lang))


@router.callback_query(CatCB.filter())
async def show_category(
    call: CallbackQuery, callback_data: CatCB, session: AsyncSession, lang: str | None
) -> None:
    cat = await catalog.get_category(session, callback_data.id)
    if cat is None or not cat.is_active:
        await call.answer(t("category_gone", lang), show_alert=True)
        return
    await call.answer()
    products, total = await catalog.list_products(
        session, category_id=cat.id, page=callback_data.page
    )
    title = t("category_title", lang, name=localized(cat, "name", lang))
    if not products:
        title = t("no_products", lang)
    await safe_edit(
        call.message,
        title,
        products_kb(products, total, callback_data.page, lang, category_id=cat.id),
    )


@router.callback_query(ProdCB.filter())
async def show_product(
    call: CallbackQuery, callback_data: ProdCB, session: AsyncSession, lang: str | None
) -> None:
    product = await catalog.get_product(session, callback_data.id)
    if product is None or product.is_archived:
        await call.answer(t("product_gone", lang), show_alert=True)
        return
    await call.answer()
    if isinstance(call.message, Message):
        markup = product_card_kb(product.id, 1, lang) if product.is_available else None
        await send_product(call.message, session, product, product_text(product, lang), markup)


@router.callback_query(QtyCB.filter())
async def change_qty(call: CallbackQuery, callback_data: QtyCB, lang: str | None) -> None:
    await call.answer()
    if isinstance(call.message, Message):
        try:
            await call.message.edit_reply_markup(
                reply_markup=product_card_kb(callback_data.id, callback_data.q, lang)
            )
        except TelegramBadRequest as exc:
            if "not modified" not in str(exc):
                raise


@router.callback_query(AddCB.filter())
async def add_to_cart(
    call: CallbackQuery,
    callback_data: AddCB,
    session: AsyncSession,
    user: User,
    lang: str | None,
) -> None:
    try:
        await cart_service.add_item(session, user.id, callback_data.id, callback_data.q)
    except cart_service.ProductUnavailable:
        await call.answer(t("product_unavailable", lang), show_alert=True)
        return
    await call.answer(t("added_to_cart", lang, qty=callback_data.q))


@router.callback_query(MenuCB.filter(F.act == "search"))
async def ask_search(call: CallbackQuery, state: FSMContext, lang: str | None) -> None:
    await call.answer()
    await state.set_state(SearchStates.query)
    if isinstance(call.message, Message):
        await call.message.answer(t("search_prompt", lang))


@router.message(SearchStates.query, F.text)
async def do_search(
    message: Message, state: FSMContext, session: AsyncSession, lang: str | None
) -> None:
    query = (message.text or "").strip()[:50]
    if not query:
        return
    await state.set_state(None)
    await state.update_data(q=query)
    products, total = await catalog.list_products(session, query=query, page=1)
    if not products:
        await message.answer(t("search_none", lang, q=query))
        return
    await message.answer(
        t("search_results", lang, q=query), reply_markup=products_kb(products, total, 1, lang)
    )


@router.callback_query(SearchPageCB.filter())
async def search_page(
    call: CallbackQuery,
    callback_data: SearchPageCB,
    state: FSMContext,
    session: AsyncSession,
    lang: str | None,
) -> None:
    query = (await state.get_data()).get("q")
    if not query:
        await call.answer(t("search_expired", lang), show_alert=True)
        return
    await call.answer()
    products, total = await catalog.list_products(session, query=query, page=callback_data.page)
    await safe_edit(
        call.message,
        t("search_results", lang, q=query),
        products_kb(products, total, callback_data.page, lang),
    )
