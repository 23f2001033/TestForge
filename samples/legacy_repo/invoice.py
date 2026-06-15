"""Invoice helpers with deliberately ordinary business logic."""


def line_total(qty: int, unit: float) -> float:
    """Return total for one invoice line."""
    if qty < 0:
        raise ValueError("quantity cannot be negative")
    return round(qty * unit, 2)


def invoice_total(lines: list[tuple[int, float]]) -> float:
    """Return total for a list of ``(quantity, unit_price)`` pairs."""
    total = 0.0
    for qty, unit in lines:
        total += line_total(qty, unit)
    return round(total, 2)

