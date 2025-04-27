def format_sum(amount, currency="UZS"):
    """Format amount with thousand separators and currency"""
    # Convert number to string with 2 decimal places
    num_str = f"{float(amount):.2f}"
    
    # Split into integer and decimal parts
    int_part, dec_part = num_str.split('.')
    
    # Remove leading zeros
    int_part = str(int(int_part))
    
    # Add spaces every 3 digits from right
    formatted_int = ''
    for i, digit in enumerate(reversed(int_part)):
        if i > 0 and i % 3 == 0:
            formatted_int = ' ' + formatted_int
        formatted_int = digit + formatted_int
    
    if currency == "USD":
        return f"{formatted_int}.{dec_part}$"
    else:
        return f"{formatted_int},{dec_part} сум"

def format_dual_currency(amount_usd, rate=13000):
    """Format amount in both USD and UZS"""
    amount_uzs = amount_usd * rate
    return f"{format_sum(amount_usd, 'USD')} ({format_sum(amount_uzs)})"