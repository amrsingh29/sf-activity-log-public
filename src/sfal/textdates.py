"""Parse dates, time ranges and durations out of free text (imports, notes).

Day-first for numeric dates (APAC convention): 07/10/2026 = 7 Oct 2026.
"""
from __future__ import annotations

import re
from datetime import date, time

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
_MON = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"

ISO = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")
D_MON_Y = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?[\s\-/.]+" + _MON + r"(?:[\s\-/.,]+(\d{2,4}))?\b", re.I)
MON_D_Y = re.compile(r"\b" + _MON + r"[\s\-.]+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?\b", re.I)
NUMERIC = re.compile(r"\b(\d{1,2})([/.\-])(\d{1,2})\2(\d{2,4})\b")
TIME_RANGE = re.compile(
    r"\b(\d{1,2})[:.](\d{2})\s*(am|pm)?\s*(?:-|–|—|to)\s*(\d{1,2})[:.](\d{2})\s*(am|pm)?\b", re.I)
DURATION = re.compile(
    r"(?:(\d+(?:\.\d+)?)\s*(?:h|hr|hrs|hour|hours)\b)?\s*(?:(\d+)\s*(?:m|min|mins|minutes)\b)?", re.I)


def _year(y: str | None, hint: int) -> int:
    if not y:
        return hint
    y = int(y)
    return y + 2000 if y < 100 else y


def find_dates(text: str, year_hint: int) -> list[date]:
    """All dates in text, in order of appearance, de-duplicated. Overlapping matches are
    resolved in favour of the earliest, longest one ("07-Oct-26" is 7 Oct 2026, not also 26 Oct)."""
    cands: list[tuple[int, int, date]] = []

    def add(m, d):
        cands.append((m.start(), m.end(), d))

    for m in ISO.finditer(text):
        try:
            add(m, date(int(m[1]), int(m[2]), int(m[3])))
        except ValueError:
            pass
    for m in D_MON_Y.finditer(text):
        try:
            add(m, date(_year(m[3], year_hint), MONTHS[m[2][:3].lower()], int(m[1])))
        except ValueError:
            pass
    for m in MON_D_Y.finditer(text):
        try:
            add(m, date(_year(m[3], year_hint), MONTHS[m[1][:3].lower()], int(m[2])))
        except ValueError:
            pass
    for m in NUMERIC.finditer(text):
        try:
            add(m, date(_year(m[4], year_hint), int(m[3]), int(m[1])))
        except ValueError:
            pass
    out, seen, taken = [], set(), []
    for s, e, d in sorted(cands, key=lambda c: (c[0], -(c[1] - c[0]))):
        if any(s < te and ts < e for ts, te in taken):
            continue
        taken.append((s, e))
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


def first_date(text: str, year_hint: int) -> date | None:
    ds = find_dates(text or "", year_hint)
    return ds[0] if ds else None


def _hm(h: str, m: str, ap: str | None) -> time | None:
    h, m = int(h), int(m)
    if ap:
        ap = ap.lower()
        if ap == "pm" and h < 12:
            h += 12
        if ap == "am" and h == 12:
            h = 0
    return time(h, m) if 0 <= h < 24 and 0 <= m < 60 else None


def time_range(text: str) -> tuple[time, time] | None:
    m = TIME_RANGE.search(text or "")
    if not m:
        return None
    end_ap = m[6]
    a = _hm(m[1], m[2], m[3] or end_ap)
    b = _hm(m[4], m[5], end_ap)
    return (a, b) if a and b else None


def duration_hours(text: str) -> float | None:
    t = (text or "").strip()
    if not t:
        return None
    if re.fullmatch(r"\d+(\.\d+)?", t):
        return float(t)
    for m in DURATION.finditer(t):
        if m[1] or m[2]:
            return round(float(m[1] or 0) + int(m[2] or 0) / 60, 2)
    return None
