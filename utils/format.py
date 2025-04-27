
def format_sum(amount: float) -> str:
    """Format amount with thousand separators"""
    return "{:,.0f} сум".format(amount)

def format_dual_currency(amount_uzs: float, amount_usd: float) -> str:
    """Format amount in both UZS and USD"""
    return f"{format_sum(amount_uzs)} / ${amount_usd:.2f}"
