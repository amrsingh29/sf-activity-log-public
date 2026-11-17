"""Activity notes - your own dated Markdown notes (read-only here; written by /log-activity-note).

Two locations, both read:
  * central:          <data_dir>/notes/**/*.md
  * customer folders: <workspace root>/**/_ActivityLogging/*.md   (when workspace.root is set)
One note = one evidence item. Its id survives moves and renames of folders (`identify`): the
note's own `note-id`, else its creation stamp and title, else its file name - with an index in
<data_dir>/note-ids.json of every path id it has had, so records logged earlier still match. The account comes from the note's `account:` header when present,
else from its folder. Activity date, strongest first: frontmatter `activity-date`,
an "Activity date:" field, a date in the title/activity line, the note's own date
(frontmatter `date`/`logged`, file name, first date in the text). The folder path is the account hint. Hours only if the note states them
("Duration: 2h", "Hours: 1.5").
"""
from __future__ import annotations

import fnmatch
import json
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import yaml

from .. import safety
from ..evidence import item, make_id
from ..textdates import duration_hours, first_date

DEFAULT_GLOB = "**/_ActivityLogging/*.md"
FRONT = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
ACTIVITY = re.compile(r"^\*\*Activity:\*\*\s*(.+)$", re.M)
# Fields may share a line, separated by "·" or "|": **Activity date:** 07-Oct-2026 · **Duration:** 3.0 h
FIELD = r"(?:^|[·|•])\s*\**\s*(?:{names})\s*\**\s*:\s*\**\s*([^·|•\n]+)"
HOURS = re.compile(FIELD.format(names="duration|hours|time spent|activity hours"), re.I | re.M)
ACTIVITY_DATE = re.compile(FIELD.format(names="activity date|date of activity|meeting date"), re.I | re.M)
SECTION = re.compile(r"^##\s+(summary|what was done)\s*$(.*?)(?=^##\s|\Z)", re.I | re.M | re.S)
SUMMARY_CHARS = 500


def parse_note(path: Path, year_hint: int) -> dict | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    meta = {}
    m = FRONT.match(text)
    if m:
        try:
            meta = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            meta = {}
        body = text[m.end():]
    else:
        body = text
    def as_date(v):
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            return v
        return first_date(str(v), year_hint) if v else None

    created = as_date(meta.get("date") or meta.get("logged") or meta.get("created")) \
        or first_date(path.name, year_hint) or first_date(body[:400], year_hint)
    fm_activity = as_date(meta.get("activity-date") or meta.get("activity_date") or meta.get("activity date"))
    act = ACTIVITY.search(body)
    title = (act.group(1).strip() if act else None) or meta.get("title") or path.stem
    # Notes are often written after the event. Activity date: explicit "Activity date:" field,
    # else a date in the title/activity line, else the note's own date.
    ad = ACTIVITY_DATE.search(body)
    d = fm_activity or (first_date(ad.group(1), year_hint) if ad else None) \
        or first_date(f"{meta.get('title') or ''} {title}", year_hint) or created
    if not d:
        return None
    sec = SECTION.search(body)
    summary = re.sub(r"\s+", " ", (sec.group(2) if sec else body)).strip()[:SUMMARY_CHARS]
    hm = HOURS.search(body)
    hours = duration_hours(hm.group(1)) if hm else None
    if hours is None and meta.get("duration-hours") not in (None, ""):
        try:
            hours = float(meta["duration-hours"])
        except (TypeError, ValueError):
            hours = None
    return {"date": d, "created": created, "title": re.sub(r"\*+", "", str(title)), "summary": summary,
            "hours": hours, "account": str(meta.get("account") or "").strip() or None,
            "note_id": str(meta.get("note-id") or "").strip() or None,
            "stamp": str(meta.get("created") or "").strip()}


def _ignored(rel: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(Path(rel).name, p) for p in patterns)


def central_dir(profile) -> Path:
    return profile.data_dir / "notes"


def _key(path: Path, n: dict) -> str:
    """What makes a note the same note wherever it lives."""
    if n["note_id"]:
        return f"id:{n['note_id']}"
    if "T" in n["stamp"]:                       # a created timestamp, as /log-activity-note writes
        return f"created:{n['stamp']}|{n['title']}"
    return f"name:{path.name}"


def identify(profile, year_hint: int) -> list[dict]:
    """Every parseable note with a stable id: {path, rel, folder, note, id, legacy_ids}.

    `legacy_ids` are the path-based ids the note has had (today's and earlier ones from
    <data_dir>/note-ids.json) - ledger rows written before a move cite those. Two files with the
    same identity (a copied note) keep their path ids, as before.
    """
    rows = []
    for path, rel, folder in note_paths(profile):
        try:
            n = parse_note(path, year_hint)
        except OSError:
            continue
        if n:
            rows.append({"path": path, "rel": rel, "folder": folder, "note": n, "key": _key(path, n)})
    counts = Counter(r["key"] for r in rows)
    index_path = profile.data_dir / "note-ids.json"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    except (OSError, json.JSONDecodeError):
        index = {}
    changed = False
    for r in rows:
        legacy = make_id("note", r["rel"])
        r["id"] = make_id("note", r["key"]) if counts[r["key"]] == 1 else legacy
        known = index.setdefault(r["id"], [])
        if legacy not in known and legacy != r["id"]:
            known.append(legacy)
            changed = True
        r["legacy_ids"] = list(known)
    if changed:
        try:
            safety.write_text(profile, index_path, json.dumps(index, indent=1, sort_keys=True))
        except (OSError, safety.BoundaryError):
            pass  # best effort: the ids still work for this run
    return rows


def _item(n: dict, nid: str, legacy_ids: list[str], rel_id: str, folder_rel: str, stem: str) -> dict:
    return item(
        id=nid, legacy_ids=legacy_ids, source="notes", kind="note", date=n["date"].isoformat(),
        hours=n["hours"], title=n["title"], preview=n["summary"],
        note_created=n["created"].isoformat() if n["created"] else None,
        folder=folder_rel, path_texts=[p for p in folder_rel.split("/") if p] + [stem],
        account_text=n["account"] or "", declared_account=n["account"],
        raw_ref=f"notes:{rel_id}")


def note_paths(profile) -> list[tuple[Path, str, str]]:
    """Every note file, wherever it lives: (path, rel id, folder relative to the workspace).

    Customer folders (workspace glob, minus ignore patterns and the log folder itself) first,
    then the central notes folder. The rel id is what evidence ids are built from.
    """
    root, central = profile.workspace_root, central_dir(profile)
    pattern = profile.source("notes").get("path") or DEFAULT_GLOB
    ignore = list(profile.data["workspace"].get("ignore") or [])
    out = []
    if root:
        for path in sorted(root.glob(pattern)):
            rel = path.relative_to(root).as_posix()
            if profile.data_dir in path.parents or _ignored(rel, ignore):
                continue
            folder = path.parent.parent if path.parent.name == "_ActivityLogging" else path.parent
            out.append((path, rel, folder.relative_to(root).as_posix() if folder != root else ""))
    if central.exists():
        for path in sorted(central.rglob("*.md")):
            out.append((path, "central/" + path.relative_to(central).as_posix(), ""))
    return out


def collect(profile, rules, d0: date, d1: date, raw_dir: Path):
    root = profile.workspace_root
    central = central_dir(profile)
    cfg = profile.source("notes")
    if not root and not central.exists():
        return [], {"source": "notes", "method": "none", "notes_scanned": 0, "notes_in_period": 0,
                    "completeness": "complete", "warnings": ["no notes yet (central notes folder empty, no workspace.root)"]}
    pattern = cfg.get("path") or DEFAULT_GLOB
    items, scanned, used = [], 0, []
    for r in identify(profile, d0.year):
        scanned += 1
        n = r["note"]
        if not (d0 <= n["date"] <= d1):
            continue  # filtered by activity date (the date in the title, else the note date)
        used.append(r["rel"])
        items.append(_item(n, r["id"], r["legacy_ids"], r["rel"], r["folder"], r["path"].stem))

    (raw_dir / "notes.json").write_text(json.dumps(used, indent=1), encoding="utf-8")
    where = " + ".join(x for x in (f"glob {pattern}" if root else "", "central notes" if central.exists() else "") if x)
    return items, {"source": "notes", "method": where, "notes_scanned": scanned,
                   "notes_in_period": len(items), "completeness": "complete"}
