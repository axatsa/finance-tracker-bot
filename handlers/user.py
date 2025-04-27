
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from db import models
from utils.format import format_sum, format_dual_currency
from utils.report import update_day_balance, generate_admin_report

router = Router()

class UserAuth(StatesGroup):
    waiting_for_cash = State()
    waiting_for_cash_currency = State()
    waiting_for_exchange_rate = State()

class UserAction(StatesGroup):
    waiting_for_expense_amount = State()
    waiting_for_expense_currency = State()
    waiting_for_expense_description = State()
    waiting_for_income_amount = State()
    waiting_for_income_currency = State()
    waiting_for_income_description = State()

@router.message(F.text == "Пользователь")
async def role_user(message: Message, state: FSMContext):
    """Handler for User button"""
    models.add_user(message.from_user.id, username="Shokhrukh", is_admin=0)
    await message.answer("Введите текущую сумму наличных:")
    await state.set_state(UserAuth.waiting_for_cash)

async def show_user_menu(message: Message):
    """Show user menu"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Добавить расход"), KeyboardButton(text="Добавить доход")],
            [KeyboardButton(text="Итог")],
            [KeyboardButton(text="Завершить день")]
        ],
        resize_keyboard=True
    )
    await message.answer("Меню пользователя:", reply_markup=keyboard)
