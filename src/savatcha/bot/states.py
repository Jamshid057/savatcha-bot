from aiogram.fsm.state import State, StatesGroup


class SearchStates(StatesGroup):
    query = State()


class Checkout(StatesGroup):
    name = State()
    phone = State()
    address = State()
    comment = State()
    receipt = State()
    confirm = State()


class AdminCategoryAdd(StatesGroup):
    name_uz = State()
    name_ru = State()


class AdminCategoryRename(StatesGroup):
    name_uz = State()
    name_ru = State()


class AdminProductAdd(StatesGroup):
    name_uz = State()
    name_ru = State()
    desc_uz = State()
    desc_ru = State()
    price = State()
    photo = State()


class AdminProductEdit(StatesGroup):
    value = State()
