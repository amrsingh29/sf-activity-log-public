"""Imported documents - Copilot or manual exports dropped into <data_dir>/inbox/.

Formats: .docx .xlsx .csv .txt .md
  * Tables: columns recognised by header synonyms (Date, Time, Duration, Subject/Meeting,
    Organizer/From, Attendees/To, Account/Customer). One evidence item per row.
  * Prose: one evidence item per line that carries a date inside the period, quoting the line.
Every imported item is completeness=partial (exports are often subsets). If a document states
its own count ("25 meetings") the parsed count is compared and a mismatch is warned.
"""
from __future__ import annotations

import csv
import json
import re
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ..evidence import item, make_id
from ..textdates import duration_hours, find_dates, first_date, time_range

EXTS = {".docx", ".xlsx", ".csv", ".txt", ".md"}
SYNONYMS = {
    "date": ["date", "day", "meeting date", "start date", "sent", "received", "date sent", "date received"],
    "time": ["time", "start time", "start", "time slot", "slot"],
    "end": ["end", "end time", "finish"],
    "duration": ["duration", "length", "hours", "hrs", "mins", "minutes"],
    "subject": ["subject", "meeting", "title", "topic", "event", "meeting title", "description", "activity"],
    "organizer": ["organizer", "organiser", "from", "sender", "owner"],
    "attendees": ["attendees", "to", "participants", "required attendees", "recipients", "invitees"],
    "account": ["account", "customer", "customer/project", "customer / project", "client", "company"],
}
STATED_COUNT = re.compile(r"\b(\d{1,4})\s+(meetings|events|emails)\b", re.I)


def _key(h: str) -> str | None:
    h = re.sub(r"\s+", " ", (h or "").strip().lower().rstrip(":"))
    for k, syns in SYNONYMS.items():
        if h in syns:
            return k
    return None


def _header(rows: list[list[str]]) -> tuple[int, dict] | None:
    for i, r in enumerate(rows[:10]):
        cols = {}
        for j, c in enumerate(r):
            k = _key(c)
            if k and k not in cols:
                cols[k] = j
        if len(cols) >= 2 and ("date" in cols or "subject" in cols):
            return i, cols
    return None


def read_file(path: Path) -> tuple[list[list[list[str]]], list[str]]:
    """Returns (tables, prose_lines)."""
    ext = path.suffix.lower()
    if ext == ".docx":
        import docx
        d = docx.Document(str(path))
        tables = [[[c.text.strip() for c in row.cells] for row in t.rows] for t in d.tables]
        return tables, [p.text.strip() for p in d.paragraphs if p.text.strip()]
    if ext == ".xlsx":
        import openpyxl
        wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
        tables = []
        for ws in wb.worksheets:
            rows = [["" if v is None else (v.isoformat() if isinstance(v, (date, datetime)) else str(v)).strip()
                     for v in r] for r in ws.iter_rows(values_only=True)]
            tables.append([r for r in rows if any(r)])
        return tables, []
    if ext == ".csv":
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
            return [[[c.strip() for c in r] for r in csv.reader(f) if any(c.strip() for c in r)]], []
    text = path.read_text(encoding="utf-8", errors="replace")
    return [], [ln.strip() for ln in text.splitlines() if ln.strip()]


def _iso(d: date, t, tz: ZoneInfo) -> str:
    return datetime.combine(d, t, tzinfo=tz).isoformat()


def parse_document(path: Path, d0: date, d1: date, tz: ZoneInfo) -> tuple[list[dict], dict]:
    tables, prose = read_file(path)
    items, rows_total, meeting_rows, skipped_nodate = [], 0, 0, 0
    fname = path.name

    for ti, rows in enumerate(tables):
        h = _header(rows)
        if not h:
            prose += [" | ".join(c for c in r if c) for r in rows]  # unknown layout -> treat as prose
            continue
        hi, cols = h
        kind = "meeting" if {"time", "duration", "end"} & cols.keys() or "organizer" in cols else "other"
        if "attendees" in cols and "organizer" in cols and "time" not in cols and "duration" not in cols:
            kind = "email"
        for ri, r in enumerate(rows[hi + 1:], start=hi + 1):
            cell = lambda k: (r[cols[k]] if k in cols and cols[k] < len(r) else "").strip()
            if not any(r):
                continue
            rows_total += 1
            if kind == "meeting":
                meeting_rows += 1
            d = first_date(cell("date"), d0.year) if cell("date") else first_date(" ".join(r), d0.year)
            if not d:
                skipped_nodate += 1
                continue
            if not (d0 <= d <= d1):
                continue
            tr = time_range(cell("time") or " ".join(r))
            start = end = None
            hours = duration_hours(cell("duration"))
            if tr:
                start, end = _iso(d, tr[0], tz), _iso(d, tr[1], tz)
                if hours is None:
                    hours = round((datetime.combine(d, tr[1]) - datetime.combine(d, tr[0])).seconds / 3600, 2)
            subject = cell("subject") or " ".join(c for c in r if c)[:120]
            items.append(item(
                id=make_id("imp", fname, str(ti), "|".join(r)), source="imports", kind=kind,
                date=d.isoformat(), start=start, end=end, hours=hours, title=subject,
                people=[p.strip() for p in re.split(r"[;,]", cell("organizer")) if p.strip()][:6],
                completeness="partial", account_text=cell("account"),
                quote=" | ".join(c for c in r if c)[:300],
                raw_ref=f"inbox/{fname}#table{ti}:row{ri}"))

    for li, line in enumerate(prose):
        if len(line) < 12:
            continue
        ds = [d for d in find_dates(line, d0.year) if d0 <= d <= d1]
        if not ds:
            continue
        tr = time_range(line)
        start = end = hours = None
        if tr:
            start, end = _iso(ds[0], tr[0], tz), _iso(ds[0], tr[1], tz)
            hours = round((datetime.combine(ds[0], tr[1]) - datetime.combine(ds[0], tr[0])).seconds / 3600, 2)
        items.append(item(
            id=make_id("imp", fname, "line", line), source="imports", kind="other",
            date=ds[0].isoformat(), start=start, end=end, hours=hours, title=line[:200],
            completeness="partial", quote=line[:300], raw_ref=f"inbox/{fname}#line{li}"))

    # The same meeting often appears in several summary tables: keep the first (date, title).
    seen, unique = set(), []
    for x in items:
        k = (x["date"], re.sub(r"\W+", " ", x["title"].lower()).strip())
        if k in seen:
            continue
        seen.add(k)
        unique.append(x)
    dupes = len(items) - len(unique)
    items = unique
    meeting_rows = sum(1 for x in items if x["kind"] == "meeting")

    full_text = " ".join(prose) + " " + " ".join(" ".join(r) for t in tables for r in t)
    stated = {m.group(2).lower(): int(m.group(1)) for m in STATED_COUNT.finditer(full_text)}
    report = {"file": fname, "tables": len(tables), "table_rows": rows_total, "items_in_period": len(items),
              "rows_without_date": skipped_nodate, "duplicates_removed": dupes}
    if "meetings" in stated and meeting_rows and stated["meetings"] != meeting_rows:
        report["count_mismatch"] = f"document states {stated['meetings']} meetings, parsed {meeting_rows}"
    return items, report


def collect(profile, rules, d0: date, d1: date, raw_dir: Path):
    inbox = profile.data_dir / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    tz = ZoneInfo(profile.timezone)
    items, files, warnings = [], [], []
    for path in sorted(inbox.iterdir()):
        if path.suffix.lower() not in EXTS or path.name.startswith(("~$", ".")):
            continue
        try:
            got, rep = parse_document(path, d0, d1, tz)
        except Exception as e:
            warnings.append(f"inbox/{path.name}: could not read ({e})")
            continue
        items += got
        files.append(rep)
        if rep.get("count_mismatch"):
            warnings.append(f"inbox/{path.name}: {rep['count_mismatch']} - some items may be missing")
    (raw_dir / "imports.json").write_text(json.dumps(files, indent=1), encoding="utf-8")
    return items, {"source": "imports", "method": "inbox files", "files": files, "items": len(items),
                   "completeness": "partial", "warnings": warnings}
