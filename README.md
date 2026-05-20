# Finance Tracker Bot

A Telegram bot for personal finance management — track income, expenses, and monthly budgets with category breakdown and scheduled reminders.

## Features
- Add income and expense records by category
- Monthly budget planning and alerts
- Statistics and charts
- Scheduled daily/weekly summaries
- Admin control panel

## Tech Stack
- Python 3.11+
- aiogram 3.x
- SQLite
- APScheduler

## Setup
```bash
pip install -r requirements.txt
cp .env.example .env  # add BOT_TOKEN
python main.py
```