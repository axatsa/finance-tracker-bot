
def format_sum(amount: float) -> str:
    """Format sum with thousand separators"""
    return f"{amount:,.0f} сум".replace(",", " ")

def format_dual_currency(amount_uzs: float, amount_usd: float) -> str:
    """Format amounts in both UZS and USD"""
    return f"{format_sum(amount_uzs)} / ${amount_usd:,.2f}"
