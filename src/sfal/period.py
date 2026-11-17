"""Resolve human period strings into an inclusive (from, to) date range."""
from __future__ import annotations

import calendar
import re
from datetime import date, timedelta

MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})


class PeriodError(ValueError):
    pass


def _month_range(y: int, m: int) -> tuple[date, date]:
    return date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])


def resolve(text: str, today: date | None = None) -> tuple[date, date]:
    """Weeks are Monday-Sunday. Month names resolve to the most recent such month."""
    today = today or date.today()
    t = (text or "").strip().lower()
    if not t:
        raise PeriodError("empty period")

    iso = re.findall(r"\d{4}-\d{2}-\d{2}", t)
    if len(iso) == 2:
        a, b = date.fromisoformat(iso[0]), date.fromisoformat(iso[1])
        if b < a:
            raise PeriodError(f"end {b} is before start {a}")
        return a, b
    if len(iso) == 1 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", t):
        d = date.fromisoformat(iso[0])
        return d, d

    monday = today - timedelta(days=today.weekday())
    if t == "today":
        return today, today
    if t == "yesterday":
        d = today - timedelta(days=1)
        return d, d
    if t == "this week":
        return monday, monday + timedelta(days=6)
    if t == "last week":
        return monday - timedelta(days=7), monday - timedelta(days=1)
    if t == "this month":
        return _month_range(today.year, today.month)
    if t == "last month":
        first = today.replace(day=1) - timedelta(days=1)
        return _month_range(first.year, first.month)
    m = re.fullmatch(r"last (\d{1,3}) days", t)
    if m:
        n = int(m.group(1))
        return today - timedelta(days=n - 1), today

    m = re.fullmatch(r"([a-z]+)(?:\s+(\d{4}))?", t)
    if m and m.group(1) in MONTHS:
        mon = MONTHS[m.group(1)]
        year = int(m.group(2)) if m.group(2) else (today.year if mon <= today.month else today.year - 1)
        return _month_range(year, mon)

    raise PeriodError(
        f"cannot understand period '{text}'. Use: today, yesterday, this week, last week, "
        "this month, last month, last N days, <month> [year], YYYY-MM-DD, or YYYY-MM-DD to YYYY-MM-DD")


def classify(d0: date, d1: date) -> dict:
    """Decide the output folder for a period from its dates (not from the words typed).

    day    - a single date                       -> <year>/days/2026-10-14
    week   - exact Monday..Sunday                -> <year>/weeks/2026-W41_2026-10-05_to_2026-10-11
    month  - exact 1st..last day of one month    -> <year>/months/2026-10_October
    range  - anything else                       -> <year>/ranges/2026-10-01_to_2026-10-03
    The year folder is the year the period starts in.
    """
    if d0 == d1:
        kind, label = "day", d0.isoformat()
    elif d0.weekday() == 0 and (d1 - d0).days == 6:
        iso_year, week, _ = d0.isocalendar()
        kind, label = "week", f"{iso_year}-W{week:02d}_{d0}_to_{d1}"
    elif d0.day == 1 and d0.year == d1.year and d0.month == d1.month and \
            d1.day == calendar.monthrange(d1.year, d1.month)[1]:
        kind, label = "month", f"{d0:%Y-%m}_{calendar.month_name[d0.month]}"
    else:
        kind, label = "range", f"{d0}_to_{d1}"
    folder = {"day": "days", "week": "weeks", "month": "months", "range": "ranges"}[kind]
    return {"kind": kind, "label": label, "relpath": f"{d0.year}/{folder}/{label}"}
