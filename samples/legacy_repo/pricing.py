"""Pricing helpers from a pretend legacy billing module."""


def apply_discount(price: float, pct: float) -> float:
    """Return price after applying a percentage discount."""
    if pct < 0:
        raise ValueError("discount cannot be negative")
    if pct > 100:
        raise ValueError("discount cannot exceed 100")
    return round(price * (1 - pct / 100), 2)


def with_tax(amount: float, rate: float) -> float:
    """Return amount with tax added."""
    if rate < 0:
        raise ValueError("tax rate cannot be negative")
    return round(amount * (1 + rate / 100), 2)


def bulk_price(unit: float, qty: int) -> float:
    """Return total price after a simple bulk discount."""
    if qty < 0:
        raise ValueError("quantity cannot be negative")
    discount = 0.9 if qty >= 10 else 1.0
    return round(unit * qty * discount, 2)

