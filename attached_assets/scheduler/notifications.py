from datetime import datetime, time
import asyncio
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from config import TIMEZONE
from utils.report import generate_daily_notification

async def send_daily_notification(bot):
    """Send daily notification to all users"""
    from db.models import get_all_users
    
    users = get_all_users()
    notification_text = generate_daily_notification()
    
    # Create keyboard with "Завершить день" button
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Завершить день")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    
    for user_id in users:
        try:
            await bot.send_message(
                user_id, 
                notification_text,
                reply_markup=keyboard
            )
        except Exception as e:
            print(f"Error sending notification to user {user_id}: {e}")
            continue

def setup_scheduler(bot):
    """Setup scheduler for daily notifications"""
    scheduler = AsyncIOScheduler()
    
    # Schedule daily notification at 20:50 Tashkent time
    scheduler.add_job(
        send_daily_notification,
        CronTrigger(hour=20, minute=50, timezone=pytz.timezone(TIMEZONE)),
        kwargs={"bot": bot}
    )
    
    return scheduler