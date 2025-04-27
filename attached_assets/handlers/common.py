
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from db import models
from handlers.admin import show_admin_menu
from handlers.user import show_user_menu

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handler for /start command"""
    user = models.get_user(message.from_user.id)
    
    if not user:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Админ"), KeyboardButton(text="Пользователь")]
            ],
            resize_keyboard=True
        )
        await message.answer(
            "Добро пожаловать! Выберите вашу роль:",
            reply_markup=keyboard
        )
    else:
        if models.is_admin(message.from_user.id):
            await show_admin_menu(message)
        else:
            await show_user_menu(message)
