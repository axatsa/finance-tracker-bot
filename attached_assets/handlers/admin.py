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

@router.message(F.text == "Добавить расход", lambda msg: models.is_admin(msg.from_user.id))
async def add_expense_admin(message: Message, state: FSMContext):
    """Admin handler for adding expense"""
    current_state = await state.get_state()
    if current_state in [AdminAuth.waiting_for_password.state, AdminAuth.waiting_for_cash.state]:
        return

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Назад")]],
        resize_keyboard=True
    )
    await message.answer("Введите сумму расхода:", reply_markup=keyboard)
    await state.set_state(AdminAction.waiting_for_expense_amount)

@router.message(AdminAction.waiting_for_expense_amount)
async def expense_amount_admin(message: Message, state: FSMContext):
    """Process expense amount for admin"""
    if message.text == "Назад":
        await state.clear()
        await show_admin_menu(message)
        return

    try:
        amount = float(message.text.replace(',', '.'))
        await state.update_data(amount=amount)
        await message.answer("Введите назначение расхода:")
        await state.set_state(AdminAction.waiting_for_expense_description)
    except ValueError:
        await message.answer("Пожалуйста, введите корректную сумму:")

@router.message(AdminAction.waiting_for_expense_description)
async def expense_description_admin(message: Message, state: FSMContext):
    """Process expense description for admin"""
    if message.text == "Назад":
        if models.is_admin(message.from_user.id):
            await state.clear()
            await show_admin_menu(message)
        return

    data = await state.get_data()
    amount = data.get("amount")
    description = message.text

    models.add_transaction(
        user_id=message.from_user.id,
        amount=amount,
        description=description,
        transaction_type="expense"
    )

    current_balance = models.get_cash_balance(message.from_user.id)
    await message.answer(f"Расход добавлен!\nТекущий баланс: {format_sum(current_balance)}")

    await show_admin_menu(message)
    await state.clear()

@router.message(F.text == "Добавить доход", lambda msg: models.is_admin(msg.from_user.id))
async def add_income_admin(message: Message, state: FSMContext):
    """Admin handler for adding income"""
    current_state = await state.get_state()
    if current_state in [AdminAuth.waiting_for_password.state, AdminAuth.waiting_for_cash.state]:
        return

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Назад")]],
        resize_keyboard=True
    )
    await message.answer("Введите сумму дохода:", reply_markup=keyboard)
    await state.set_state(AdminAction.waiting_for_income_amount)

@router.message(AdminAction.waiting_for_income_amount)
async def income_amount_admin(message: Message, state: FSMContext):
    """Process income amount for admin"""
    if message.text == "Назад":
        if models.is_admin(message.from_user.id):
            await state.clear()
            await show_admin_menu(message)
        return

    try:
        amount = float(message.text.replace(',', '.'))
        await state.update_data(amount=amount)
        await message.answer("Введите источник дохода:")
        await state.set_state(AdminAction.waiting_for_income_description)
    except ValueError:
        await message.answer("Пожалуйста, введите корректную сумму:")

@router.message(AdminAction.waiting_for_income_description)
async def income_description_admin(message: Message, state: FSMContext):
    """Process income description for admin"""
    if message.text == "Назад":
        await state.clear()
        await show_admin_menu(message)
        return

    data = await state.get_data()
    amount = data.get("amount")
    description = message.text

    models.add_transaction(
        user_id=message.from_user.id,
        amount=amount,
        description=description,
        transaction_type="income"
    )

    current_balance = models.get_cash_balance(message.from_user.id)
    await message.answer(f"Доход добавлен!\nТекущий баланс: {format_sum(current_balance)}")

    await show_admin_menu(message)
    await state.clear()

@router.message(F.text == "Наличные Шохруха", lambda msg: models.is_admin(msg.from_user.id))
async def show_shokhrukh_cash(message: Message):
    """Show Shokhrukh's cash and transactions"""
    # Get user with non-admin role
    conn = models.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, cash_balance FROM users WHERE is_admin = 0 LIMIT 1")
    shokhrukh = cursor.fetchone()
    conn.close()

    if not shokhrukh:
        await message.answer("Пользователь Шохрух не найден в системе.")
        return

    user_id, username, balance = shokhrukh

    # Get transactions
    transactions = models.get_user_transactions(user_id)

    response = f"Данные по наличным Шохруха:\n\nТекущий баланс: {format_sum(balance)}\n\nОперации:"

    if not transactions:
        response += "\nНет операций."
    else:
        for amount, description, tr_type, date in transactions[:10]:  # Show last 10 transactions
            sign = "+" if tr_type == "income" else "-"
            date_fmt = date.split(".")[0] if isinstance(date, str) else date  # Format date
            response += f"\n{date_fmt}: {sign}{format_sum(amount)} - {description}"

    await message.answer(response)

@router.message(F.text == "Итог", lambda msg: models.is_admin(msg.from_user.id))
async def show_summary_admin(message: Message):
    """Show summary for admin"""
    transactions = models.get_user_transactions(message.from_user.id)
    summary = models.get_user_summary(user_id=message.from_user.id)

    response = "Ваш финансовый отчет:\n\nИстория операций:\n"

    for amount, description, tr_type, date in transactions:
        operation = "Приход" if tr_type == "income" else "Расход"
        response += f"\n{date}: {operation}\n"
        response += f"Сумма: {format_sum(amount)}\n"
        response += f"Назначение: {description}\n"
        response += "------------------------"

    response += f"\n\nИтоговый баланс: {summary['balance']:.2f} сум"

    await message.answer(response)

@router.message(F.text == "Очистить историю", lambda msg: models.is_admin(msg.from_user.id))
async def clear_history_confirm(message: Message):
    """Ask for confirmation before clearing history"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да"), KeyboardButton(text="Нет")]
        ],
        resize_keyboard=True
    )
    await message.answer("Вы точно хотите очистить историю?", reply_markup=keyboard)

@router.message(F.text == "Да", lambda msg: models.is_admin(msg.from_user.id))
async def clear_history_yes(message: Message):
    """Clear transaction history after confirmation"""
    conn = models.get_connection()
    cursor = conn.cursor()

    # Clear all transactions
    cursor.execute("DELETE FROM transactions")

    # Reset all balances to 0
    cursor.execute("UPDATE users SET cash_balance = 0")

    conn.commit()
    conn.close()

    await message.answer("История операций очищена.")
    await show_admin_menu(message)

@router.message(F.text == "Нет", lambda msg: models.is_admin(msg.from_user.id))
async def clear_history_no(message: Message):
    """Cancel history clearing"""
    await message.answer("Очистка истории отменена.")
    await show_admin_menu(message)
@router.message(Command("clear_db"), lambda msg: models.is_admin(msg.from_user.id))
async def clear_db(message: Message):
    """Clear entire database"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да, очистить БД"), KeyboardButton(text="Отмена")]
        ],
        resize_keyboard=True
    )
    await message.answer("⚠️ Вы уверены что хотите полностью очистить базу данных? Это действие нельзя отменить.", reply_markup=keyboard)

@router.message(F.text == "Да, очистить БД", lambda msg: models.is_admin(msg.from_user.id))
async def confirm_clear_db(message: Message):
    """Confirm and clear database"""
    models.clear_database()
    await message.answer("База данных очищена.")
    await show_admin_menu(message)

@router.message(F.text == "Отмена", lambda msg: models.is_admin(msg.from_user.id))
async def cancel_clear_db(message: Message):
    """Cancel database clearing"""
    await message.answer("Очистка базы данных отменена.")
    await show_admin_menu(message)