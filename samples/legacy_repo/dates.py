"""Date helpers from a legacy scheduling module."""

from datetime import date


def days_between(a: date, b: date) -> int:
    """Return the absolute number of days between two dates."""
    return abs((b - a).days)


def is_weekend(d: date) -> bool:
    """Return True when a date falls on Saturday or Sunday."""
    return d.weekday() >= 5

