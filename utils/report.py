
from db.models import get_connection
from utils.format import format_sum

def update_day_balance(user_id):
    """Update previous day balance with current balance for next day reporting"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT cash_balance FROM users WHERE user_id = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    
    if result:
        current_balance = result[0]
        
        cursor.execute(
            "UPDATE users SET previous_balance = ? WHERE user_id = ?",
            (current_balance, user_id)
        )
        
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False

def generate_admin_report():
    """Generate a financial report for the admin"""
    # Get user with non-admin role
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, cash_balance, previous_balance FROM users WHERE is_admin = 0 LIMIT 1")
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return "Пользователь не найден в системе."
    
    user_id, username, balance, previous_balance = user
    
    # Get transactions for today
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT amount, description, transaction_type, datetime(created_at, 'localtime') " +
        "FROM transactions WHERE user_id = ? AND date(created_at) = date('now') " +
        "ORDER BY created_at DESC",
        (user_id,)
    )
    today_transactions = cursor.fetchall()
    conn.close()
    
    # Calculate total income and expenses for today
    total_income = 0
    total_expense = 0
    for amount, _, tr_type, _ in today_transactions:
        if tr_type == "income":
            total_income += amount
        else:
            total_expense += amount
    
    # Generate report
    report = f"📊 Финансовый отчет {username}\n\n"
    report += f"💰 Начальный баланс: {format_sum(previous_balance)}\n"
    report += f"➕ Доходы за сегодня: {format_sum(total_income)}\n"
    report += f"➖ Расходы за сегодня: {format_sum(total_expense)}\n"
    report += f"💵 Текущий баланс: {format_sum(balance)}\n\n"
    
    if today_transactions:
        report += "🧾 Операции за сегодня:\n"
        for amount, description, tr_type, date in today_transactions:
            sign = "➕" if tr_type == "income" else "➖"
            time = date.split(" ")[1][:5] if " " in date else "00:00"
            report += f"{time} {sign} {format_sum(amount)} - {description}\n"
    else:
        report += "Нет операций за сегодня."
    
    return report

def generate_daily_notification(user_id):
    """Generate daily notification message for user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get user data
    cursor.execute("SELECT username, cash_balance, previous_balance FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    
    if not user_data:
        conn.close()
        return "Пользователь не найден в системе."
    
    username, balance, previous_balance = user_data
    
    # Get today's transactions
    cursor.execute(
        "SELECT amount, description, transaction_type, datetime(created_at, 'localtime') " +
        "FROM transactions WHERE user_id = ? AND date(created_at) = date('now') " +
        "ORDER BY created_at DESC",
        (user_id,)
    )
    today_transactions = cursor.fetchall()
    
    # Calculate totals
    total_income = 0
    total_expense = 0
    for amount, _, tr_type, _ in today_transactions:
        if tr_type == "income":
            total_income += amount
        else:
            total_expense += amount
    
    # Format the notification
    notification = f"📅 Ежедневное уведомление для {username}\n\n"
    notification += f"💰 Начальный баланс: {format_sum(previous_balance)}\n"
    notification += f"➕ Доходы за сегодня: {format_sum(total_income)}\n"
    notification += f"➖ Расходы за сегодня: {format_sum(total_expense)}\n"
    notification += f"💵 Текущий баланс: {format_sum(balance)}\n\n"
    
    # Calculate balance difference
    balance_diff = balance - previous_balance
    if balance_diff > 0:
        notification += f"📈 Ваш баланс вырос на {format_sum(balance_diff)} сегодня\n"
    elif balance_diff < 0:
        notification += f"📉 Ваш баланс уменьшился на {format_sum(abs(balance_diff))} сегодня\n"
    else:
        notification += "⚖️ Ваш баланс не изменился сегодня\n"
    
    conn.close()
    return notification
