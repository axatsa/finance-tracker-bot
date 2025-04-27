
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from db import models
from utils.format import format_sum
from config import ADMIN_PASSWORD

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

@router.message(F.text == "Добавить расход", lambda msg: models.is_admin(msg.from_user.id))
async def add_expense_admin(message: Message, state: FSMContext):
    """Admin handler for adding expense"""
    await message.answer("Введите сумму расхода:")
    await state.set_state(AdminAction.waiting_for_expense_amount)

@router.message(AdminAction.waiting_for_expense_amount)
async def process_expense_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
        await state.update_data(amount=amount)
        await message.answer("Введите описание расхода:")
        await state.set_state(AdminAction.waiting_for_expense_description)
    except ValueError:
        await message.answer("Пожалуйста, введите корректную сумму:")

@router.message(AdminAction.waiting_for_expense_description)
async def process_expense_description(message: Message, state: FSMContext):
    data = await state.get_data()
    models.add_transaction(
        message.from_user.id,
        data['amount'],
        message.text,
        "expense"
    )
    await message.answer(f"Расход добавлен: {data['amount']} сум - {message.text}")
    await show_admin_menu(message)
    await state.clear()

@router.message(F.text == "Добавить доход", lambda msg: models.is_admin(msg.from_user.id))
async def add_income_admin(message: Message, state: FSMContext):
    """Admin handler for adding income"""
    await message.answer("Введите сумму дохода:")
    await state.set_state(AdminAction.waiting_for_income_amount)

@router.message(AdminAction.waiting_for_income_amount)
async def process_income_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
        await state.update_data(amount=amount)
        await message.answer("Введите описание дохода:")
        await state.set_state(AdminAction.waiting_for_income_description)
    except ValueError:
        await message.answer("Пожалуйста, введите корректную сумму:")

@router.message(AdminAction.waiting_for_income_description)
async def process_income_description(message: Message, state: FSMContext):
    data = await state.get_data()
    models.add_transaction(
        message.from_user.id,
        data['amount'],
        message.text,
        "income"
    )
    await message.answer(f"Доход добавлен: {data['amount']} сум - {message.text}")
    await show_admin_menu(message)
    await state.clear()

@router.message(F.text == "Наличные Шохруха", lambda msg: models.is_admin(msg.from_user.id))
async def show_shohruh_cash(message: Message):
    """Show Shohruh's cash balance"""
    balance = models.get_cash_balance(message.from_user.id)
    transactions = models.get_user_transactions(message.from_user.id)
    
    response = f"Данные по наличным Шохруха:\n\nТекущий баланс: {format_sum(balance)}\n\nОперации:"
    
    if not transactions:
        response += "\nНет операций"
    else:
        for amount, description, tr_type, date in transactions[:10]:
            sign = "+" if tr_type == "income" else "-"
            response += f"\n{date}: {sign}{format_sum(amount)} - {description}"
    
    await message.answer(response)

@router.message(F.text == "Итог", lambda msg: models.is_admin(msg.from_user.id))
async def show_summary_admin(message: Message):
    """Show summary for admin"""
    from datetime import datetime
    
    user_id = message.from_user.id
    balance = models.get_cash_balance(user_id)
    transactions = models.get_user_transactions(user_id)
    
    total_expense = 0
    total_income = 0
    operations = []
    
    for amount, description, tr_type, _ in transactions:
        if tr_type == "income":
            total_income += amount
            operations.append(f"➕ {format_sum(amount)} - {description}")
        else:
            total_expense += amount
            operations.append(f"➖ {format_sum(amount)} - {description}")
    
    current_date = datetime.now().strftime("%d.%m.%Y")
    initial_balance = balance + total_expense - total_income
    current_balance = initial_balance - total_expense + total_income
    
    response = f"📅 Дата: {current_date}\n"
    response += f"💰 Баланс: {format_sum(initial_balance)}\n\n"
    response += "📋 Перечень операций:\n"
    if operations:
        response += "\n".join(operations)
    else:
        response += "Нет операций\n"
    response += f"\n💸 Общий расход: {format_sum(total_expense)}"
    response += f"\n💵 Текущий остаток: {format_sum(current_balance)}"
    
    await message.answer(response)

@router.message(F.text == "Очистить историю", lambda msg: models.is_admin(msg.from_user.id))
async def clear_history(message: Message):
    """Clear transaction history"""
    models.clear_database()
    await message.answer("История операций очищена")
    await show_admin_menu(message)
