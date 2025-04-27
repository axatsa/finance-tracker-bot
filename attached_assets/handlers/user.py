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

@router.message(UserAuth.waiting_for_cash)
async def user_cash(message: Message, state: FSMContext):
    """Set initial cash balance for user"""
    try:
        cash_balance = float(message.text.replace(',', '.'))
        
        # Set cash balance in UZS directly
        models.set_cash_balance(message.from_user.id, cash_balance, "UZS")
        
        # Set previous balance to current balance
        models.update_day_balance(message.from_user.id)
        
        await show_user_menu(message)
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректную сумму:")

@router.message(UserAuth.waiting_for_cash_currency)
async def user_cash_currency(message: Message, state: FSMContext):
    """Set currency for initial cash balance"""
    data = await state.get_data()
    cash_balance = data.get("cash_balance")
    
    if message.text not in ["UZS", "USD"]:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="UZS"), KeyboardButton(text="USD")]
            ],
            resize_keyboard=True
        )
        await message.answer("Пожалуйста, выберите валюту из предложенных вариантов:", reply_markup=keyboard)
        return
    
    # Save currency
    currency = message.text
    
    if currency == "USD":
        # Set cash balance in USD
        models.set_cash_balance(message.from_user.id, cash_balance, "USD")
        # Ask for exchange rate
        await message.answer("Введите курс доллара (по умолчанию 13000):")
        await state.set_state(UserAuth.waiting_for_exchange_rate)
    else:
        # Set cash balance in UZS
        models.set_cash_balance(message.from_user.id, cash_balance, "UZS")
        # Set previous balance to current balance
        models.update_day_balance(message.from_user.id)
        
        await show_user_menu(message)
        await state.clear()

@router.message(UserAuth.waiting_for_exchange_rate)
async def user_exchange_rate(message: Message, state: FSMContext):
    """Set exchange rate for USD to UZS"""
    try:
        exchange_rate = float(message.text.replace(',', '.'))
        models.set_exchange_rate(message.from_user.id, exchange_rate)
        
        # Set previous balance to current balance
        models.update_day_balance(message.from_user.id)
        
        await show_user_menu(message)
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число для курса:")

async def show_user_menu(message: Message):
    """Show user menu"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Добавить расход"), KeyboardButton(text="Добавить доход")],
            [KeyboardButton(text="Итог"), KeyboardButton(text="Завершить день")]
        ],
        resize_keyboard=True
    )
    
    await message.answer("Меню пользователя:", reply_markup=keyboard)

@router.message(F.text == "Добавить расход", lambda msg: not models.is_admin(msg.from_user.id))
async def add_expense_user(message: Message, state: FSMContext):
    """User handler for adding expense"""
    current_state = await state.get_state()
    if current_state in [UserAuth.waiting_for_cash]:
        return
        
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Назад")]],
        resize_keyboard=True
    )
    await message.answer("Введите сумму расхода:", reply_markup=keyboard)
    await state.set_state(UserAction.waiting_for_expense_amount)

@router.message(UserAction.waiting_for_expense_amount)
async def expense_amount_user(message: Message, state: FSMContext):
    """Process expense amount for user"""
    if message.text == "Назад":
        await state.clear()
        await show_user_menu(message)
        return
        
    try:
        amount = float(message.text.replace(',', '.'))
        await state.update_data(amount=amount)
        
        # Skip currency selection and go straight to description
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Назад")]],
            resize_keyboard=True
        )
        await message.answer("Введите назначение расхода:", reply_markup=keyboard)
        await state.set_state(UserAction.waiting_for_expense_description)
    except ValueError:
        await message.answer("Пожалуйста, введите корректную сумму:")

@router.message(UserAction.waiting_for_expense_description)
async def expense_description_user(message: Message, state: FSMContext):
    """Process expense description for user"""
    if message.text == "Назад":
        await state.clear()
        await show_user_menu(message)
        return
    
    data = await state.get_data()
    amount = data.get("amount")
    description = message.text
    
    # Always use UZS
    models.add_transaction(
        user_id=message.from_user.id,
        amount=amount,
        description=description,
        transaction_type="expense",
        currency="UZS"  # Always use UZS
    )
    
    # Get updated balance
    balance = models.get_cash_balance(message.from_user.id)
    await message.answer(f"Расход добавлен!\nТекущий баланс: {format_sum(balance)}")
    
    await show_user_menu(message)
    await state.clear()

@router.message(F.text == "Добавить доход", lambda msg: not models.is_admin(msg.from_user.id))
async def add_income_user(message: Message, state: FSMContext):
    """User handler for adding income"""
    current_state = await state.get_state()
    if current_state in [UserAuth.waiting_for_cash]:
        return
        
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Назад")]],
        resize_keyboard=True
    )
    await message.answer("Введите сумму дохода:", reply_markup=keyboard)
    await state.set_state(UserAction.waiting_for_income_amount)

@router.message(UserAction.waiting_for_income_amount)
async def income_amount_user(message: Message, state: FSMContext):
    """Process income amount for user"""
    if message.text == "Назад":
        await state.clear()
        await show_user_menu(message)
        return
        
    try:
        amount = float(message.text.replace(',', '.'))
        await state.update_data(amount=amount)
        
        # Skip currency selection and go straight to description
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Назад")]],
            resize_keyboard=True
        )
        await message.answer("Введите источник дохода:", reply_markup=keyboard)
        await state.set_state(UserAction.waiting_for_income_description)
    except ValueError:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Назад")]],
            resize_keyboard=True
        )
        await message.answer("Пожалуйста, введите корректную сумму:", reply_markup=keyboard)

@router.message(UserAction.waiting_for_income_description)
async def income_description_user(message: Message, state: FSMContext):
    """Process income description for user"""
    if message.text == "Назад":
        await state.clear()
        await show_user_menu(message)
        return
    
    data = await state.get_data()
    amount = data.get("amount")
    description = message.text
    
    # Always use UZS
    models.add_transaction(
        user_id=message.from_user.id,
        amount=amount,
        description=description,
        transaction_type="income",
        currency="UZS"  # Always use UZS
    )
    
    # Get updated balance
    balance = models.get_cash_balance(message.from_user.id)
    await message.answer(f"Доход добавлен!\nТекущий баланс: {format_sum(balance)}")
    
    await show_user_menu(message)
    await state.clear()


@router.message(F.text == "Итог", lambda msg: not models.is_admin(msg.from_user.id))
async def show_summary_user(message: Message, state: FSMContext):
    """Show summary for user in the new format"""
    current_state = await state.get_state()
    if current_state in [UserAuth.waiting_for_cash]:
        return
    
    report = generate_admin_report()
    await message.answer(report)

@router.message(F.text == "Завершить день", lambda msg: not models.is_admin(msg.from_user.id))
async def finish_day_user(message: Message):
    """Finish the day - update previous balance and send report to admin"""
    # Get admin user
    admin_id = models.get_admin_id()
    if not admin_id:
        await message.answer("Ошибка: администратор не найден в системе.")
        return
    
    # Generate report
    report = generate_admin_report()
    
    # Send report to admin
    from aiogram import Bot
    from config import BOT_TOKEN
    
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(admin_id, "📊 <b>Ежедневный финансовый отчет от Шохруха:</b>\n\n" + report)
        
        # Update previous day balance for next day
        if update_day_balance(message.from_user.id):
            await message.answer("День успешно завершен! Отчет отправлен администратору.")
        else:
            await message.answer("Ошибка при обновлении баланса.")
    except Exception as e:
        await message.answer(f"Ошибка при отправке отчета: {str(e)}")
    finally:
        await bot.session.close()
