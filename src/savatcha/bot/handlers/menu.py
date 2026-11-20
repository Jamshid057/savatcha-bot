"""Asosiy menyu tugmalari: har qanday FSM holatida ishlaydi va holatni tozalaydi."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.bot.handlers.cart import show_cart
from savatcha.bot.handlers.catalog import show_categories
from savatcha.bot.handlers.orders import show_my_orders
from savatcha.bot.keyboards.lang import lang_keyboard
from savatcha.bot.keyboards.main_menu import menu_labels
from savatcha.core.config import get_settings
from savatcha.core.db.models import User
from savatcha.core.i18n import t

router = Router(name="menu")


@router.message(F.text.in_(menu_labels("menu_catalog")))
async def menu_catalog(
    message: Message, state: FSMContext, session: AsyncSession, lang: str | None
) -> None:
    await state.clear()
    await show_categories(message, session, lang)


@router.message(F.text.in_(menu_labels("menu_cart")))
async def menu_cart(
    message: Message, state: FSMContext, session: AsyncSession, user: User, lang: str | None
) -> None:
    await state.clear()
    await show_cart(message, session, user, lang)


@router.message(F.text.in_(menu_labels("menu_orders")))
async def menu_orders(
    message: Message, state: FSMContext, session: AsyncSession, user: User, lang: str | None
) -> None:
    await state.clear()
    await show_my_orders(message, session, user, lang)


@router.message(F.text.in_(menu_labels("menu_lang")))
async def menu_lang(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(t("choose_lang"), reply_markup=lang_keyboard())


@router.message(F.text.in_(menu_labels("menu_contact")))
async def menu_contact(message: Message, state: FSMContext, lang: str | None) -> None:
    await state.clear()
    s = get_settings()
    await message.answer(
        t("contact_text", lang, name=s.shop_name, phone=s.shop_phone, hours=s.shop_hours)
    )
