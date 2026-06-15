"""String cleanup helpers used in old import jobs."""

import re


def slugify(s: str) -> str:
    """Convert text into a lower-case dash-separated slug."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower())
    return cleaned.strip("-")


def truncate(s: str, n: int) -> str:
    """Return text clipped to at most n characters."""
    if n < 0:
        raise ValueError("length cannot be negative")
    if len(s) <= n:
        return s
    if n <= 3:
        return s[:n]
    return s[: n - 3] + "..."

