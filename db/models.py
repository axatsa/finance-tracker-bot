
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

def set_cash_balance(user_id: int, cash_balance: float, currency: str = "UZS") -> None:
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

def add_transaction(user_id: int, amount: float, description: str, transaction_type: str, currency: str = "UZS") -> None:
    """Add a transaction for a user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get exchange rate for the user
    cursor.execute("SELECT exchange_rate FROM users WHERE user_id = ?", (user_id,))
    exchange_rate = cursor.fetchone()[0] or 13000
    
    amount_usd = 0
    amount_uzs = 0
    
    if currency == "USD":
        amount_usd = amount
        amount_uzs = amount * exchange_rate
    else:
        amount_uzs = amount
        amount_usd = amount / exchange_rate
    
    # Add transaction
    cursor.execute(
        "INSERT INTO transactions (user_id, amount, amount_usd, description, transaction_type, currency) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, amount_uzs, amount_usd, description, transaction_type, currency)
    )
    
    # Update balance
    if transaction_type == "income":
        cursor.execute(
            "UPDATE users SET cash_balance = cash_balance + ?, cash_balance_usd = cash_balance_usd + ? WHERE user_id = ?",
            (amount_uzs, amount_usd, user_id)
        )
    else:
        cursor.execute(
            "UPDATE users SET cash_balance = cash_balance - ?, cash_balance_usd = cash_balance_usd - ? WHERE user_id = ?",
            (amount_uzs, amount_usd, user_id)
        )
    
    conn.commit()
    conn.close()

def get_user_transactions(user_id: int) -> List[Tuple]:
    """Get all transactions for a user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT amount, description, transaction_type, datetime(created_at, 'localtime') FROM transactions WHERE user_id = ? ORDER BY created_at ASC",
        (user_id,)
    )
    transactions = cursor.fetchall()
    
    conn.close()
    return transactions

def get_admin_id() -> Optional[int]:
    """Get the first admin user ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT user_id FROM users WHERE is_admin = 1 LIMIT 1")
    result = cursor.fetchone()
    
    conn.close()
    return result[0] if result else None

def clear_database() -> None:
    """Clear all data from database"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM transactions")
    cursor.execute("DELETE FROM users")
    
    conn.commit()
    conn.close()

def get_user(user_id: int) -> tuple:
    """Get user data by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    conn.close()
    return user

def get_all_users() -> list:
    """Get all user IDs"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT user_id FROM users")
    users = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    return users

def get_user_summary(user_id: int) -> dict:
    """Get user summary with balance"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT cash_balance FROM users WHERE user_id = ?", (user_id,))
    balance = cursor.fetchone()[0] if cursor.fetchone() else 0
    
    conn.close()
    return {'balance': balance}
