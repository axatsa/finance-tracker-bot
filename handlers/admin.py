
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from db import models
from utils.format import format_sum

router = Router()

class AdminAuth(StatesGroup):
    waiting_for_password = State()
    waiting_for_cash = State()

class AdminAction(StatesGroup):
    waiting_for_expense_amount = State()
    waiting_for_expense_description = State()
    waiting_for_income_amount = State()
    waiting_for_income_description = State()

@router.message(F.text == "Админ")
async def role_admin(message: Message, state: FSMContext):
    """Handler for Admin button"""
    await message.answer("Введите пароль администратора:")
    await state.set_state(AdminAuth.waiting_for_password)

@router.message(AdminAuth.waiting_for_password)
async def admin_password(message: Message, state: FSMContext):
    """Check admin password"""
    from config import ADMIN_PASSWORD

    if message.text == ADMIN_PASSWORD:
        models.set_user_admin(message.from_user.id)
        await message.answer("Доступ администратора предоставлен. Введите текущую сумму наличных:")
        await state.set_state(AdminAuth.waiting_for_cash)
    else:
        await message.answer("Неверный пароль. Попробуйте еще раз:")

@router.message(AdminAuth.waiting_for_cash)
async def admin_cash(message: Message, state: FSMContext):
    """Set initial cash balance for admin"""
    try:
        cash_balance = float(message.text.replace(',', '.'))
        models.set_cash_balance(message.from_user.id, cash_balance)
        await show_admin_menu(message)
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректную сумму:")

async def show_admin_menu(message: Message):
    """Show admin menu"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Добавить расход"), KeyboardButton(text="Добавить доход")],
            [KeyboardButton(text="Наличные Шохруха"), KeyboardButton(text="Итог")],
            [KeyboardButton(text="Очистить историю")]
        ],
        resize_keyboard=True
    )
    await message.answer("Меню администратора:", reply_markup=keyboard)
