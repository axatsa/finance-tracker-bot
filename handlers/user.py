from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from db import models

@router.message(Command("clear_db"))
async def clear_db(message: Message):
    """Clear entire database"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Да, очистить базу"), KeyboardButton(text="❌ Нет, отмена")]
        ],
        resize_keyboard=True
    )
    await message.answer("⚠️ Вы уверены, что хотите полностью очистить базу данных?\nЭто действие нельзя отменить!", reply_markup=keyboard)

@router.message(F.text == "✅ Да, очистить базу")
async def confirm_clear_db(message: Message):
    """Confirm and clear database"""
    models.clear_database()
    await message.answer("База данных очищена!")
    await show_user_menu(message)

@router.message(F.text == "❌ Нет, отмена")
async def cancel_clear_db(message: Message):
    """Cancel database clearing"""
    await message.answer("Очистка базы данных отменена.")
    await show_user_menu(message)
from utils.format import format_sum
from utils.report import generate_admin_report, update_day_balance

router = Router()

class UserAction(StatesGroup):
    waiting_for_expense_amount = State()
    waiting_for_expense_description = State()
    waiting_for_income_amount = State()
    waiting_for_income_description = State()
    waiting_for_cash = State()

@router.message(F.text == "Пользователь")
async def role_user(message: Message, state: FSMContext):
    """Handler for User button"""
    models.add_user(message.from_user.id, username="Shokhrukh", is_admin=0)
    await message.answer("Введите текущую сумму наличных:")
    await state.set_state(UserAction.waiting_for_cash)

@router.message(UserAction.waiting_for_cash)
async def user_cash(message: Message, state: FSMContext):
    """Set initial cash balance for user"""
    try:
        cash_balance = float(message.text.replace(',', '.'))
        models.set_cash_balance(message.from_user.id, cash_balance)
        await show_user_menu(message)
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректную сумму:")

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

@router.message(F.text == "Добавить расход")
async def add_expense_user(message: Message, state: FSMContext):
    """User handler for adding expense"""
    await message.answer("Введите сумму расхода:")
    await state.set_state(UserAction.waiting_for_expense_amount)

@router.message(UserAction.waiting_for_expense_amount)
async def expense_amount_user(message: Message, state: FSMContext):
    """Process expense amount for user"""
    try:
        amount = float(message.text.replace(',', '.'))
        await state.update_data(amount=amount)
        await message.answer("Введите описание расхода:")
        await state.set_state(UserAction.waiting_for_expense_description)
    except ValueError:
        await message.answer("Пожалуйста, введите корректную сумму:")

@router.message(UserAction.waiting_for_expense_description)
async def expense_description_user(message: Message, state: FSMContext):
    """Process expense description for user"""
    data = await state.get_data()
    amount = data.get("amount")
    description = message.text

    models.add_transaction(
        user_id=message.from_user.id,
        amount=amount,
        description=description,
        transaction_type="expense"
    )

    await message.answer(f"Расход добавлен: {amount} сум - {description}")
    await show_user_menu(message)
    await state.clear()

@router.message(F.text == "Добавить доход")
async def add_income_user(message: Message, state: FSMContext):
    """User handler for adding income"""
    await message.answer("Введите сумму дохода:")
    await state.set_state(UserAction.waiting_for_income_amount)

@router.message(UserAction.waiting_for_income_amount)
async def income_amount_user(message: Message, state: FSMContext):
    """Process income amount for user"""
    try:
        amount = float(message.text.replace(',', '.'))
        await state.update_data(amount=amount)
        await message.answer("Введите описание дохода:")
        await state.set_state(UserAction.waiting_for_income_description)
    except ValueError:
        await message.answer("Пожалуйста, введите корректную сумму:")

@router.message(UserAction.waiting_for_income_description)
async def income_description_user(message: Message, state: FSMContext):
    """Process income description for user"""
    data = await state.get_data()
    amount = data.get("amount")
    description = message.text

    models.add_transaction(
        user_id=message.from_user.id,
        amount=amount,
        description=description,
        transaction_type="income"
    )

    await message.answer(f"Доход добавлен: {amount} сум - {description}")
    await show_user_menu(message)
    await state.clear()

@router.message(F.text == "Итог")
async def show_summary_user(message: Message):
    """Show summary for user"""
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

@router.message(F.text == "Завершить день", lambda msg: not models.is_admin(msg.from_user.id))
async def finish_day_user(message: Message):
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

@router.message(F.text == "✅ Да, завершить день")
async def confirm_finish_day(message: Message):
    """Handle day finish confirmation"""
    # Get admin user
    admin_id = models.get_admin_id()
    if not admin_id:
        await message.answer("Ошибка: администратор не найден в системе.")
        return

    # Generate report before clearing
    report = generate_admin_report()
    
    # Get current balance and update for next day
    user_id = message.from_user.id
    balance = models.get_cash_balance(user_id)
    models.set_cash_balance(user_id, balance)
    update_day_balance(user_id)
    
    # Clear transactions for new day
    models.clear_user_transactions(user_id)

    # Get user menu keyboard
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Добавить расход"), KeyboardButton(text="Добавить доход")],
            [KeyboardButton(text="Итог")],
            [KeyboardButton(text="Завершить день")]
        ],
        resize_keyboard=True
    )
    
    # Send confirmation to user
    await message.answer("День завершен ✅\nОтчет отправлен администратору.", reply_markup=keyboard)

    # Send report to admin
    bot = message.bot
    await bot.send_message(admin_id, f"📊 Ежедневный отчет:\n\n{report}")

@router.message(F.text == "❌ Нет, продолжить работу")
async def cancel_finish_day(message: Message):
    """Handle day finish cancellation"""
    await show_user_menu(message)