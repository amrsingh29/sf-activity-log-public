"""Catalog - one local page with every activity note, ledger record and rendered period.

    collect(profile, rules) -> dict     notes, records, periods (plain data; tested)
    build(profile, rules) -> dict       writes <data_dir>/catalog/index-modern.html

Notes are found exactly as the weekly notes source finds them (customer folders and the
central notes folder), so the page and the log never disagree. A note counts as logged when
an active ledger row cites it as evidence. The page is read-only and inside data_dir (the
write boundary); it is rebuilt after every note save, commit and render. No AI involved.
"""
from __future__ import annotations

import html
import json
import re
from datetime import date, datetime
from pathlib import Path

from . import safety
from .accounts import Registry
from .ledger import Ledger
from .render import is_held
from .sources import notes as notes_src

FRONT = re.compile(r"^---\s*\n.*?\n---\s*\n", re.S)
FOLLOW = re.compile(r"^##\s+(follow-ups|follow ups|next steps)\s*$(.*?)(?=^##\s|\Z)", re.I | re.M | re.S)
HEADING = re.compile(r"^#\s+(.+)$", re.M)
DATES = re.compile(r"(\d{4}-\d{2}-\d{2})")
MAX_TEXT = 40000


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _follow_ups(body: str) -> list[str]:
    out = []
    for m in FOLLOW.finditer(body):
        for line in m.group(2).splitlines():
            line = line.strip()
            if line.startswith(("- ", "* ")):
                out.append(re.sub(r"^[-*]\s+(\[[ xX]\]\s+)?", "", line))
    return out[:20]


def _notes(profile, rules, logged: dict[str, list[str]]) -> list[dict]:
    registry = Registry(profile.accounts, rules.internal_account)
    internal = profile.data["workspace"].get("internal_folders") or []
    year = date.today().year
    out = []
    for r in notes_src.identify(profile, year):
        path, rel, folder, n = r["path"], r["rel"], r["folder"], r["note"]
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        nid = r["id"]
        body = FRONT.sub("", text, count=1)
        title = n["title"]
        if title == path.stem:          # no title field: the first heading reads better than a file name
            h = HEADING.search(body)
            title = h.group(1).strip() if h else title
        declared = registry.canonical(n["account"] or "")
        if declared:
            acc = {"name": declared, "kind": registry.kind_of(declared)}
        else:
            in_internal = any(folder == f or folder.startswith(f + "/") for f in internal)
            acc = registry.match([title, n["account"] or ""] + [p for p in folder.split("/") if p],
                                 [], folder_hint=folder or None, internal_only=in_internal) or {}
        out.append({
            "id": nid, "title": title, "date": n["date"].isoformat(),
            "created": n["created"].isoformat() if n["created"] else "",
            "account": acc.get("name") or n["account"] or "", "account_kind": acc.get("kind") or "",
            "hours": n["hours"], "summary": n["summary"], "follow_ups": _follow_ups(body),
            "where": "central" if rel.startswith("central/") else "customer folder",
            "folder": folder, "path": str(path), "url": path.as_uri(),
            "logged_by": sorted({e for i in [nid] + r["legacy_ids"] for e in logged.get(i, [])}),
            "legacy_ids": r["legacy_ids"], "text": body[:MAX_TEXT],
        })
    out.sort(key=lambda x: (x["date"], x["created"]), reverse=True)
    return out


def _records(rows: list[dict], note_of: dict[str, str]) -> list[dict]:
    """note_of: every id a note has had (stable or path-based) -> its current id."""
    out = []
    for r in rows:
        refs = [note_of.get(x, x) for x in r["evidence_refs"] or []]
        out.append({
            "id": r["entry_id"], "account": r["account_name"], "account_kind": r["account_kind"],
            "type": r["activity_type"], "status": r["status"], "date": r["activity_date"],
            "start": r.get("start_date") or "", "act": r["activity_hours"], "prep": r["prep_hours"],
            "notes": r["notes"], "opportunity": r["opportunity"], "no_opp_reason": r["no_opp_reason"],
            "area": "; ".join(r["solution_area"] or []), "to_confirm": r["to_confirm"],
            "voided": bool(r["voided"]), "voided_by": r["voided_by"], "supersedes": r["supersedes"],
            "held": (not r["voided"]) and is_held(r), "evidence": refs,
            "note_ids": sorted({x for x in refs if x in note_of.values()}), "added": r["added_on"],
        })
    out.sort(key=lambda x: (x["date"], x["id"]), reverse=True)
    return out


def _periods(profile) -> list[dict]:
    out = []
    root = profile.data_dir / "output"
    for folder in sorted(root.glob("*/*/*")) if root.exists() else []:
        if not folder.is_dir() or folder.parent.name not in ("days", "weeks", "months", "ranges"):
            continue
        snap = {}
        sp = folder / ".snapshot.json"
        if sp.exists():
            try:
                snap = json.loads(sp.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                snap = {}
        rows = snap.get("rows") or []
        ready = [x for x in rows if not x.get("held")]
        md = sorted(folder.glob("Salesforce_Activity_Log_*.md"))
        xlsx = sorted(folder.glob("Salesforce_Activity_Log_*.xlsx"))
        runs = folder / "runs.md"
        renders = sum(1 for line in runs.read_text(encoding="utf-8").splitlines()
                      if line.startswith("| 2")) if runs.exists() else 0
        ds = DATES.findall(folder.name)
        out.append({
            "kind": folder.parent.name[:-1], "label": folder.name,
            "from": ds[0] if ds else "", "to": ds[-1] if ds else "",
            "generated": snap.get("generated") or "", "records": len(rows), "held": len(rows) - len(ready),
            "act": round(sum(x.get("activity_hours") or 0 for x in ready), 2),
            "prep": round(sum(x.get("prep_hours") or 0 for x in ready), 2),
            "accounts": sorted({x.get("account") or "" for x in rows} - {""}),
            "md": md[-1].as_uri() if md else "", "xlsx": xlsx[-1].as_uri() if xlsx else "",
            "folder": folder.as_uri(), "renders": renders,
        })
    out.sort(key=lambda x: (x["to"], x["from"]), reverse=True)
    return out


def collect(profile, rules) -> dict:
    rows = Ledger(profile.data_dir).rows()
    logged: dict[str, list[str]] = {}
    for r in rows:
        if not r["voided"]:
            for ref in r["evidence_refs"] or []:
                logged.setdefault(ref, []).append(r["entry_id"])
    notes = _notes(profile, rules, logged)
    return {"owner": profile.owner, "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "notes": notes,
            "records": _records(rows, {i: n["id"] for n in notes for i in [n["id"]] + n["legacy_ids"]}),
            "periods": _periods(profile)}


def build(profile, rules) -> dict:
    data = collect(profile, rules)
    path = safety.write_text(profile, profile.data_dir / "catalog" / "index-modern.html", modern_page(data))
    return {"path": str(path), "url": path.as_uri(), "notes": len(data["notes"]),
            "records": sum(1 for r in data["records"] if not r["voided"]), "periods": len(data["periods"])}


def try_build(profile, rules) -> str | None:
    """Rebuild after a write; a catalog problem must never fail the note, commit or render."""
    try:
        return build(profile, rules)["path"]
    except Exception:  # noqa: BLE001 - best effort by design
        return None


# ---------------------------------------------------------------- page
MODERN = Path(__file__).resolve().parent / "catalog_modern.html"


def modern_page(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return (MODERN.read_text(encoding="utf-8").replace("__OWNER__", html.escape(data["owner"] or ""))
            .replace("__DATA__", payload))
