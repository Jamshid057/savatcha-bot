from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from savatcha.bot.keyboards.lang import LangCB, lang_keyboard
from savatcha.bot.keyboards.main_menu import main_menu
from savatcha.core.db.models import User
from savatcha.core.i18n import SUPPORTED, t
from savatcha.core.repo import users

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, user: User) -> None:
    await state.clear()
    if user.lang is None:
        await message.answer(t("choose_lang"), reply_markup=lang_keyboard())
        return
    name = message.from_user.first_name if message.from_user else ""
    await message.answer(t("welcome", user.lang, name=name), reply_markup=main_menu(user.lang))


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, lang: str | None) -> None:
    await state.clear()
    await message.answer(t("cancelled", lang), reply_markup=main_menu(lang))


@router.callback_query(LangCB.filter())
async def pick_lang(
    call: CallbackQuery, callback_data: LangCB, session: AsyncSession, user: User
) -> None:
    if callback_data.code not in SUPPORTED:
        await call.answer()
        return
    await call.answer()
    await users.set_lang(session, user, callback_data.code)
    lang = callback_data.code
    if isinstance(call.message, Message):
        await call.message.edit_text(t("lang_saved", lang))
        await call.message.answer(
            t("welcome", lang, name=call.from_user.first_name), reply_markup=main_menu(lang)
        )
