
import sqlite3
import datetime
from typing import List, Dict, Tuple, Optional, Any


def get_connection():
    """Get SQLite connection"""
    return sqlite3.connect('finance.db')


def initialize_db():
    """Initialize database tables if they don't exist"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    is_admin INTEGER DEFAULT 0,
    cash_balance REAL DEFAULT 0,
    cash_balance_usd REAL DEFAULT 0,
    previous_balance REAL DEFAULT 0,
    previous_balance_usd REAL DEFAULT 0,
    exchange_rate REAL DEFAULT 13000
                   )
    ''')
    
    # Create transactions table
    cursor.execute('''
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    amount_usd REAL DEFAULT 0,
    description TEXT,
    transaction_type TEXT,
    currency TEXT DEFAULT 'UZS',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()


def add_user(user_id: int, username: str, is_admin: int = 0) -> None:
    """Add a new user or update existing one"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT OR REPLACE INTO users (user_id, username, is_admin) VALUES (?, ?, ?)",
        (user_id, username, is_admin)
    )
    
    conn.commit()
    conn.close()


def get_user(user_id: int) -> Optional[Tuple]:
    """Get user by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    conn.close()
    return user


def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    conn.close()
    return bool(result and result[0] == 1)


def set_user_admin(user_id: int) -> None:
    """Set user as admin"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT OR REPLACE INTO users (user_id, is_admin) VALUES (?, 1)",
        (user_id,)
    )
    
    conn.commit()
    conn.close()


def set_cash_balance(user_id, cash_balance, currency="UZS"):
    """Set cash balance for a user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if currency == "USD":
        cursor.execute(
            "UPDATE users SET cash_balance_usd = ? WHERE user_id = ?",
            (cash_balance, user_id)
        )
    else:
        cursor.execute(
            "UPDATE users SET cash_balance = ? WHERE user_id = ?",
            (cash_balance, user_id)
        )
    
    conn.commit()
    conn.close()

def get_cash_balance(user_id: int) -> float:
    """Get cash balance for user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT cash_balance FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    conn.close()
    return result[0] if result else 0.0


def add_transaction(user_id, amount, description, transaction_type, currency="UZS"):
    """Add a transaction for a user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    exchange_rate = get_exchange_rate(user_id)
    
    amount_usd = 0
    amount_uzs = 0
    
    if currency == "USD":
        amount_usd = amount
        amount_uzs = amount * exchange_rate
    else:
        amount_uzs = amount
        amount_usd = amount / exchange_rate
    
    cursor.execute(
        "INSERT INTO transactions (user_id, amount, amount_usd, description, transaction_type, currency) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, amount_uzs if currency == "UZS" else amount_usd * exchange_rate, 
         amount_usd, description, transaction_type, currency)
    )
    
    # Update user balance
    if transaction_type == "income":
        if currency == "USD":
            cursor.execute(
                "UPDATE users SET cash_balance_usd = cash_balance_usd + ? WHERE user_id = ?",
                (amount_usd, user_id)
            )
            cursor.execute(
                "UPDATE users SET cash_balance = cash_balance + ? WHERE user_id = ?",
                (amount_uzs, user_id)
            )
        else:
            cursor.execute(
                "UPDATE users SET cash_balance = cash_balance + ? WHERE user_id = ?",
                (amount_uzs, user_id)
            )
            cursor.execute(
                "UPDATE users SET cash_balance_usd = cash_balance_usd + ? WHERE user_id = ?",
                (amount_usd, user_id)
            )
    else:  # expense
        if currency == "USD":
            cursor.execute(
                "UPDATE users SET cash_balance_usd = cash_balance_usd - ? WHERE user_id = ?",
                (amount_usd, user_id)
            )
            cursor.execute(
                "UPDATE users SET cash_balance = cash_balance - ? WHERE user_id = ?",
                (amount_uzs, user_id)
            )
        else:
            cursor.execute(
                "UPDATE users SET cash_balance = cash_balance - ? WHERE user_id = ?",
                (amount_uzs, user_id)
            )
            cursor.execute(
                "UPDATE users SET cash_balance_usd = cash_balance_usd - ? WHERE user_id = ?",
                (amount_usd, user_id)
            )
    
    conn.commit()
    conn.close()

    def get_exchange_rate(user_id):
        conn = get_connection()
        cursor = conn.cursor()
    
    cursor.execute(
        "SELECT exchange_rate FROM users WHERE user_id = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result and result[0] else 13000  # Default to 13000 if not set

def set_exchange_rate(user_id, rate):
    """Set exchange rate for a user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE users SET exchange_rate = ? WHERE user_id = ?",
        (rate, user_id)
    )
    
    conn.commit()
    conn.close()

def update_day_balance(user_id):
    """Update previous day balance with current balance"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT cash_balance, cash_balance_usd FROM users WHERE user_id = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    
    if result:
        current_balance, current_balance_usd = result
        
        cursor.execute(
            "UPDATE users SET previous_balance = ?, previous_balance_usd = ? WHERE user_id = ?",
            (current_balance, current_balance_usd, user_id)
        )
        
        conn.commit()
    
    conn.close()
    return result is not None


def get_user_transactions(user_id: int) -> List[Tuple]:
    """Get all transactions for a user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT amount, description, transaction_type, datetime(date, 'localtime') FROM transactions WHERE user_id = ? ORDER BY date DESC",
        (user_id,)
    )
    transactions = cursor.fetchall()
    
    conn.close()
    return transactions


def get_user_summary(user_id: int) -> Dict[str, Any]:
    """Get financial summary for a user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get balance
    cursor.execute("SELECT cash_balance FROM users WHERE user_id = ?", (user_id,))
    balance = cursor.fetchone()[0]
    
    # Get total income
    cursor.execute(
        "SELECT SUM(amount) FROM transactions WHERE user_id = ? AND transaction_type = 'income'",
        (user_id,)
    )
    total_income = cursor.fetchone()[0] or 0
    
    # Get total expenses
    cursor.execute(
        "SELECT SUM(amount) FROM transactions WHERE user_id = ? AND transaction_type = 'expense'",
        (user_id,)
    )
    total_expenses = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return {
        "balance": balance,
        "total_income": total_income,
        "total_expenses": total_expenses
    }


def get_all_users() -> List[Tuple]:
    """Get all users"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT user_id, username, is_admin FROM users")
    users = cursor.fetchall()
    
    conn.close()
    return users
def clear_database():
    """Clear all data from database"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Drop existing tables
    cursor.execute("DROP TABLE IF EXISTS transactions")
    cursor.execute("DROP TABLE IF EXISTS users")
    
    # Reinitialize tables
    initialize_db()
    
    conn.commit()
    conn.close()
