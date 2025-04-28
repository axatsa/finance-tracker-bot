from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from datetime import datetime
from db import models
from utils.format import format_sum
from utils.report import generate_admin_report, update_day_balance
from config import ADMIN_PASSWORD

router = Router()

@router.message(Command("clear_db"), lambda msg: models.is_admin(msg.from_user.id))
async def clear_db(message: Message):
    """Clear entire database"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Да, очистить базу"), KeyboardButton(text="❌ Нет, отмена")]
        ],
        resize_keyboard=True
    )
    await message.answer("⚠️ Вы уверены, что хотите полностью очистить базу данных?\nЭто действие нельзя отменить!", reply_markup=keyboard)

@router.message(F.text == "✅ Да, очистить базу", lambda msg: models.is_admin(msg.from_user.id))
async def confirm_clear_db(message: Message):
    """Confirm and clear database"""
    models.clear_database()
    await message.answer("База данных очищена!")
    await show_admin_menu(message)

@router.message(F.text == "❌ Нет, отмена", lambda msg: models.is_admin(msg.from_user.id))
async def cancel_clear_db(message: Message):
    """Cancel database clearing"""
    await message.answer("Очистка базы данных отменена.")
    await show_admin_menu(message)

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
            [KeyboardButton(text="Очистить историю"), KeyboardButton(text="Завершить день")]
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
    
    # Get updated balance
    balance = models.get_cash_balance(message.from_user.id)
    formatted_amount = format_sum(data['amount'])
    await message.answer(f"Расход добавлен: {formatted_amount} - {message.text}\nТекущий баланс: {format_sum(balance)}")
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
    
    # Get updated balance
    balance = models.get_cash_balance(message.from_user.id)
    formatted_amount = format_sum(data['amount'])
    await message.answer(f"Доход добавлен: {formatted_amount} - {message.text}\nТекущий баланс: {format_sum(balance)}")
    await show_admin_menu(message)
    await state.clear()

@router.message(F.text == "Наличные Шохруха", lambda msg: models.is_admin(msg.from_user.id))
async def show_shohruh_cash(message: Message):
    """Show Shohruh's report to admin"""
    # Get user with non-admin role
    conn = models.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE is_admin = 0 LIMIT 1")
    user = cursor.fetchone()
    conn.close()

    if not user:
        await message.answer("Пользователь Шохрух не найден в системе.")
        return

    if not user:
        await message.answer("Пользователь Шохрух не найден в системе.")
        return
        
    user_id = user[0]  # Get user_id from query result
    balance = models.get_cash_balance(user_id)
    transactions = models.get_user_transactions(user_id)

    total_expense = 0
    total_income = 0
    operations = []

    for amount, description, tr_type, _ in transactions:
        if tr_type == "income":
            total_income += amount
            operations.append(f"Приход: {format_sum(amount)} - {description}")
        else:
            total_expense += amount
            operations.append(f"Расход: {format_sum(amount)} - {description}")

    current_date = datetime.now().strftime("%d.%m.%Y")
    initial_balance = balance + total_expense - total_income
    current_balance = initial_balance - total_expense + total_income

    response = f"📅 Дата: {current_date}\n\n"
    response += f"💰 Баланс: {format_sum(initial_balance)}\n\n"
    response += "📋 Перечень операций:\n"
    if operations:
        response += "\n".join(operations) + "\n"
    else:
        response += "Нет операций\n"
    response += f"\n💸 Общий расход: {format_sum(total_expense)}\n\n"
    response += f"💵 Текущий остаток: {format_sum(current_balance)}"

    await message.answer(response)

@router.message(F.text == "Завершить день", lambda msg: models.is_admin(msg.from_user.id))
async def finish_day_admin(message: Message):
    """Show confirmation buttons for finishing the day"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Да, завершить день"), KeyboardButton(text="❌ Нет, продолжить работу")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        "Вы уверены, что хотите завершить день?\n"
        "Напоминаем, что в 20:50 вам придет уведомление о необходимости сдать отчет.",
        reply_markup=keyboard
    )

@router.message(F.text == "✅ Да, завершить день", lambda msg: models.is_admin(msg.from_user.id))
async def confirm_finish_day_admin(message: Message):
    """Handle day finish confirmation for admin"""
    user_id = message.from_user.id
    
    # Get admin's transactions and generate their report
    balance = models.get_cash_balance(user_id)
    transactions = models.get_user_transactions(user_id)

    total_expense = 0
    total_income = 0
    operations = []

    for amount, description, tr_type, _ in transactions:
        if tr_type == "income":
            total_income += amount
            operations.append(f"Приход: {format_sum(amount)} - {description}")
        else:
            total_expense += amount
            operations.append(f"Расход: {format_sum(amount)} - {description}")

    current_date = datetime.now().strftime("%d.%m.%Y")
    initial_balance = balance + total_expense - total_income
    current_balance = initial_balance - total_expense + total_income

    report = f"📅 Дата: {current_date}\n\n"
    report += f"💰 Баланс: {format_sum(initial_balance)}\n\n"
    report += "📋 Перечень операций:\n"
    if operations:
        report += "\n".join(operations) + "\n"
    else:
        report += "Нет операций\n"
    report += f"\n💸 Общий расход: {format_sum(total_expense)}\n\n"
    report += f"💵 Текущий остаток: {format_sum(current_balance)}"

    # Update balance for next day and clear transactions
    models.set_cash_balance(user_id, current_balance)
    models.clear_user_transactions(user_id)
    update_day_balance(user_id)

    # Send confirmation and admin's own report
    await message.answer("День завершен ✅")
    await message.answer(report)
    await show_admin_menu(message)

@router.message(F.text == "❌ Нет, продолжить работу", lambda msg: models.is_admin(msg.from_user.id))
async def cancel_finish_day_admin(message: Message):
    """Handle day finish cancellation for admin"""
    await show_admin_menu(message)

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
            operations.append(f"Приход: {format_sum(amount)} - {description}")
        else:
            total_expense += amount
            operations.append(f"Расход: {format_sum(amount)} - {description}")

    current_date = datetime.now().strftime("%d.%m.%Y")
    initial_balance = balance + total_expense - total_income
    current_balance = initial_balance - total_expense + total_income

    response = f"📅 Дата: {current_date}\n\n"
    response += f"💰 Баланс: {format_sum(initial_balance)}\n\n"
    response += "📋 Перечень операций:\n"
    if operations:
        response += "\n".join(operations) + "\n"
    else:
        response += "Нет операций\n"
    response += f"\n💸 Общий расход: {format_sum(total_expense)}\n\n"
    response += f"💵 Текущий остаток: {format_sum(current_balance)}"

    await message.answer(response)

@router.message(F.text == "Очистить историю", lambda msg: models.is_admin(msg.from_user.id))
async def clear_history(message: Message):
    """Clear transaction history"""
    models.clear_database()
    await message.answer("История операций очищена")
    await show_admin_menu(message)