"""/log-activity-note - turn what you did into detailed activity notes while it is fresh.

context()   the day's meetings, sent mail and touched files (with account hints), the account list,
            the save mode and notes already written that day. Cached for detail().
detail()    full detail for chosen items only: invite description + attendee RSVPs, full email
            bodies of the thread (boilerplate and quoted history removed), file titles/authors.
targets()   where a note for an account may be saved: central, or folders matched to the account
            by the registry (internal work -> the first internal folder). Never an AI-chosen path.
save()      validate (required fields, hours vs evidence) and write. Writes only to
            <data_dir>/notes/ or to `_ActivityLogging/` in a matched folder. Never overwrites.

Note content standard: summary; per activity what / people / outcomes & decisions / next steps;
follow-ups; optional cited background; anything missing listed under "To confirm".
The header carries account, activity date and duration for the weekly run.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

from .accounts import Registry
from .sources.notes import central_dir

SKIP_DIRS = {".git", "node_modules", "__pycache__", "_ActivityLogging", "_SFActivityLog"}
MAX_DEPTH = 3
BODY_CHARS = 4000
HOURS_TOLERANCE = 0.01
QUOTED = re.compile(r"(?m)^\s*(From:\s.+\n(?:.*\n){0,4}?\s*(Sent|Date):\s|-{2,}\s*Original Message|On .+ wrote:\s*$)")
TEAMS = re.compile(r"(?is)_{8,}.*?(microsoft teams|join:|meeting id).*?(_{8,}|$)")
SIGNATURE = re.compile(r"(?is)\n\s*(regards|best regards|thanks|thank you|cheers),?\s*\n.*$")


class NoteError(Exception):
    pass


def slug(text: str, words: int = 6, chars: int = 50) -> str:
    """Readable slug cut at a word boundary: 'HelixGPT right-sizing PSR sync' -> 'helixgpt-right-sizing-psr-sync'."""
    out = []
    for w in re.findall(r"[a-z0-9]+", (text or "").lower()):
        if len(out) >= words or len("-".join(out + [w])) > chars:
            break
        out.append(w)
    return "-".join(out) or "note"


# ---------------------------------------------------------------- context + detail
def _cache_file(profile, day: date) -> Path:
    return profile.data_dir / "cache" / "note-context" / f"{day.isoformat()}.json"


def context(profile, rules, day: date) -> dict:
    """What happened on `day`, from the enabled sources (calendar, email, files)."""
    import tempfile

    from .prepare import ENGINE_SOURCES, match_accounts
    from .sources.notes import parse_note

    registry = Registry(profile.accounts, rules.internal_account)
    items, warnings = [], []
    raw = Path(tempfile.mkdtemp(prefix="sfal-note-"))
    for s in ("calendar", "email", "files"):
        if not profile.source(s).get("enabled"):
            continue
        try:
            got, _ = ENGINE_SOURCES[s].collect(profile, rules, day, day, raw)
            items += [x for x in got if not x["excluded"]]
        except Exception as e:
            warnings.append(f"{s}: {e}")
    match_accounts(items, registry, profile.data["workspace"].get("internal_folders") or [])
    items.sort(key=lambda x: (x.get("start") or "", x["source"]))

    cache = _cache_file(profile, day)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(items, default=str, ensure_ascii=False), encoding="utf-8")

    def brief(x):
        a = x.get("account_hint") or {}
        return {k: v for k, v in {
            "id": x["id"], "source": x["source"], "time": (x.get("start") or "")[11:16] or None,
            "hours": x.get("hours"), "title": x["title"], "account": a.get("name"),
            "account_candidates": a.get("candidates"), "people": (x.get("people") or [])[:6],
            "messages": x.get("message_count"), "has_description": bool(x.get("description")) or None,
            "files": [f["file"].rsplit("/", 1)[-1] for f in (x.get("files") or [])][:6] or None,
        }.items() if v not in (None, [], "")}

    written = []
    for folder, pattern in ((central_dir(profile), "**/*.md"), (profile.workspace_root, "**/_ActivityLogging/*.md")):
        if not folder or not folder.exists():
            continue
        for p in folder.glob(pattern):
            if p.stem.startswith(day.isoformat()):
                n = parse_note(p, day.year)
                if n:
                    written.append({"title": n["title"], "account": n["account"], "path": str(p)})
    return {"ok": True, "date": day.isoformat(), "save_to": save_mode(profile),
            "gbrain": bool(profile.source("gbrain").get("enabled")),
            "accounts": [a["name"] for a in profile.accounts],
            "today": [brief(x) for x in items], "notes_already_written": written, "warnings": warnings}


def clean_body(text: str) -> str:
    t = (text or "").replace("\r", "")
    t = TEAMS.sub("", t)
    m = QUOTED.search(t)
    if m:
        t = t[:m.start()]
    t = SIGNATURE.sub("", t)
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()[:BODY_CHARS]


def _email_detail(profile, x: dict, day: date) -> dict:
    from .sources import email as em
    cfg = profile.source("email")
    key = em.thread_subject(x["title"]).lower()
    messages = []
    for mb in x.get("mailboxes") or cfg.get("mailboxes") or ["Sent Items"]:
        got = em.fetch_mailbox(cfg.get("account") or "Exchange", mb, day, day, preview=12000)
        for m in got["messages"]:
            if em.thread_subject(m["subject"]).lower() == key:
                messages.append({"date": m["date"], "subject": m["subject"], "from": m["sender"],
                                 "to": len(m["to"]), "cc": len(m["cc"]),
                                 "attachments": [a for a in m["attachments"] if not em.INLINE_IMAGE.match(a)],
                                 "body": clean_body(m["preview"])})
    messages.sort(key=lambda m: m["date"])
    return {"id": x["id"], "source": "email", "title": x["title"], "messages": messages}


def detail(profile, rules, day: date, ids: list[str]) -> dict:
    cache = _cache_file(profile, day)
    if not cache.exists():
        context(profile, rules, day)
    items = {x["id"]: x for x in json.loads(cache.read_text())}
    out, missing = [], []
    for i in ids:
        x = items.get(i)
        if not x:
            missing.append(i)
            continue
        if x["source"] == "calendar":
            out.append({"id": i, "source": "calendar", "title": x["title"], "start": x.get("start"), "end": x.get("end"),
                        "hours": x.get("hours"), "organizer": x.get("organizer_name") or x.get("organizer"),
                        "my_status": x.get("my_status"), "location": x.get("location"),
                        "attendees": x.get("attendees") or [], "description": x.get("description") or ""})
        elif x["source"] == "email":
            out.append(_email_detail(profile, x, day))
        elif x["source"] == "files":
            out.append({"id": i, "source": "files", "title": x["title"], "files": x.get("files") or []})
        else:
            out.append({"id": i, "source": x["source"], "title": x["title"]})
    return {"ok": True, "date": day.isoformat(), "items": out, **({"missing": missing} if missing else {})}


# ---------------------------------------------------------------- targets
def save_mode(profile) -> str:
    return profile.source("notes").get("save_to") or "central"


def _walk_dirs(root: Path):
    base = len(root.parts)
    for dirpath, dirnames, _ in os.walk(root):
        d = Path(dirpath)
        depth = len(d.parts) - base
        dirnames[:] = [n for n in dirnames if not n.startswith((".", "~")) and n not in SKIP_DIRS]
        if depth >= MAX_DEPTH:
            dirnames[:] = []
        if d != root:
            yield d, depth


def account_folders(profile, rules, account: str) -> list[dict]:
    """Folders under workspace.root for an account: name/alias match, or internal folders for internal work."""
    root = profile.workspace_root
    if not root or not root.exists():
        return []
    registry = Registry(profile.accounts, rules.internal_account)
    canon = registry.canonical(account)
    if canon == rules.internal_account:
        out = []
        for name in profile.data["workspace"].get("internal_folders") or []:
            d = root / name
            if d.is_dir():
                out.append({"path": str(d), "relative": name, "depth": 1, "exact": True,
                            "has_notes": (d / "_ActivityLogging").is_dir()})
        return out
    if not canon:
        return []
    entry = next(e for e in registry.entries if e["name"] == canon)
    out = []
    for d, depth in _walk_dirs(root):
        name = d.name.lower()
        if not any(pat.search(name) for _, pat in entry["patterns"]):
            continue
        exact = any(name == a.lower() for a, _ in entry["patterns"])
        out.append({"path": str(d), "relative": d.relative_to(root).as_posix(), "depth": depth,
                    "exact": exact, "has_notes": (d / "_ActivityLogging").is_dir()})
    out.sort(key=lambda f: (not f["has_notes"], not f["exact"], f["depth"], f["relative"]))
    return out


def targets(profile, rules, account: str) -> dict:
    central = {"target": "central", "where": str(central_dir(profile))}
    if save_mode(profile) != "customer_folder":
        return {"ok": True, "mode": "central", "recommended": central, "options": [central]}
    folders = account_folders(profile, rules, account)
    options = [{"target": f["path"], "where": f["relative"] + "/_ActivityLogging"} for f in folders[:5]] + [central]
    if not folders:
        return {"ok": True, "mode": "customer_folder", "recommended": central, "options": options,
                "note": f"no folder matches '{account}' - saving centrally; add an alias to the account to change this"}
    best = folders[0]
    sure = len(folders) == 1 or (best["has_notes"] and not folders[1]["has_notes"]) or \
        (best["exact"] and not folders[1]["exact"])
    return {"ok": True, "mode": "customer_folder", "recommended": options[0] if sure else None,
            "options": options, **({} if sure else {"ask": "several folders match - ask the user which one"})}


# ---------------------------------------------------------------- validate + render + save
def _num(v):
    if v in (None, "", "[to confirm]"):
        return None
    return float(v)


STOP_WORDS = {"the", "and", "with", "for", "sync", "call", "meeting", "weekly", "daily", "discussion", "on", "of"}


def _words(t: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (t or "").lower()) if len(w) > 2}


def _looks_like(a: str, b: str) -> bool:
    """Same activity? Shared distinctive words (not just 'weekly sync') and overall overlap."""
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return False
    shared = wa & wb
    return bool(shared - STOP_WORDS) and len(shared) / min(len(wa), len(wb)) >= 0.5


def _day_items(profile, day: str) -> dict:
    cache = _cache_file(profile, date.fromisoformat(day))
    return {x["id"]: x for x in json.loads(cache.read_text())} if cache.exists() else {}


def check_mixups(profile, note: dict) -> list[str]:
    """An activity that looks like a same-day meeting it does not cite is probably that meeting -
    or two activities were merged. Either cite it, or confirm it is different (not_meetings)."""
    items = _day_items(profile, note["activity_date"])
    meetings = [x for x in items.values() if x["source"] == "calendar"]
    errs = []
    for i, a in enumerate(note.get("activities") or [], 1):
        cited = set(a.get("evidence") or [])
        excused = set(a.get("not_meetings") or [])
        for m in meetings:
            if m["id"] in cited or m["id"] in excused:
                continue
            if _looks_like(a.get("title", ""), m["title"]):
                errs.append(f"activity {i} '{a.get('title')}' looks like the meeting {m['id']} '{m['title']}' "
                            f"({(m.get('start') or '')[11:16]}, {m.get('hours') or 0:g}h), which it does not cite. "
                            "If it is that meeting, cite it and use its content and hours; if it is a different "
                            "activity, ask the user and put the id in not_meetings")
    return errs


def check_hours(profile, note: dict) -> list[str]:
    """An activity's duration must equal its meeting's length, unless the user stated it (with their words)."""
    items = _day_items(profile, note["activity_date"])
    errs = []
    for i, a in enumerate(note.get("activities") or [], 1):
        h = _num(a.get("duration_hours"))
        if h is None:
            continue
        if a.get("hours_source") == "user":
            if not str(a.get("hours_quote") or "").strip():
                errs.append(f"activity {i}: user-stated hours need hours_quote - the user's own words, e.g. 'about an hour'")
            continue
        meetings = [items[e] for e in a.get("evidence") or [] if e in items and items[e]["source"] == "calendar"]
        if not meetings:
            errs.append(f"activity {i}: {h:g}h has no meeting behind it - use '[to confirm]', or set "
                        "hours_source 'user' if the user said it")
        elif abs(h - sum(m.get("hours") or 0 for m in meetings)) > HOURS_TOLERANCE:
            errs.append(f"activity {i}: {h:g}h but the meeting is {sum(m.get('hours') or 0 for m in meetings):g}h - "
                        "use the meeting length, or set hours_source 'user' if the user said otherwise")
    return errs


def _fmt_hours(h) -> str:
    return "[to confirm]" if h is None else f"{h:g} h"


def render_note(n: dict) -> str:
    d = date.fromisoformat(n["activity_date"])
    acts = n.get("activities") or []
    known = [_num(a.get("duration_hours")) for a in acts]
    total = None if not acts or any(h is None for h in known) else round(sum(known), 2)
    head = {"type": "activity-note", "note-id": n.get("note_id") or uuid.uuid4().hex[:16],
            "title": n["title"], "account": n["account"],
            "activity-date": n["activity_date"],
            "created": datetime.now().astimezone().isoformat(timespec="minutes"), "source": "log-activity-note"}
    if total is not None:
        head["duration-hours"] = total
    ev = [e for a in acts for e in a.get("evidence") or []]
    if ev:
        head["evidence"] = ev
    L = ["---", yaml.safe_dump(head, sort_keys=False, allow_unicode=True).strip(), "---", "",
         f"# {n['title']}", "",
         f"**Account:** {n['account']} · **Activity date:** {d:%a %d-%b-%Y} · **Duration:** {_fmt_hours(total)}", "",
         "## Summary", "", n["summary"].strip(), ""]
    for a in acts:
        hours = _fmt_hours(_num(a.get("duration_hours")))
        if a.get("hours_source") == "user" and a.get("hours_quote"):
            hours += f' (you said: "{a["hours_quote"]}")'
        when = " · ".join(x for x in (a.get("time") or "", hours) if x)
        L += [f"## {a['title']}", "", f"*{when}*" if when else "", ""]
        if a.get("what"):
            L += [a["what"].strip(), ""]
        for label, key in (("Context", "context"), ("Discussed", "discussed"),
                           ("Outcomes & decisions", "outcomes"), ("Next steps", "next_steps")):
            if a.get(key):
                L += [f"**{label}**", ""] + [f"- {x}" for x in a[key]] + [""]
        if a.get("people"):
            L += ["**People**", "", "| Person | Role / status |", "|---|---|"] + \
                 [f"| {p.get('name', '')} | {p.get('role') or p.get('status') or ''} |" for p in a["people"]] + [""]
    if n.get("follow_ups"):
        L += ["## Follow-ups", ""] + [f"- [ ] {x}" for x in n["follow_ups"]] + [""]
    if n.get("background"):
        L += ["## Background", ""] + [f"- `{b['source']}` - {b['text']}" if b.get("source") else f"- {b['text']}"
                                      for b in n["background"]] + [""]
    if n.get("to_confirm"):
        L += ["## To confirm", ""] + [f"- {x}" for x in n["to_confirm"]] + [""]
    return "\n".join(x for i, x in enumerate(L) if not (x == "" and i and L[i - 1] == ""))


def validate(profile, note: dict) -> list[str]:
    errs = [f"note needs '{k}'" for k in ("title", "account", "activity_date", "summary") if not str(note.get(k) or "").strip()]
    try:
        date.fromisoformat(note.get("activity_date") or "")
    except ValueError:
        errs.append("activity_date must be YYYY-MM-DD")
        return errs
    acts = note.get("activities") or []
    if not acts:
        errs.append("note needs at least one activity (title + what)")
    for i, a in enumerate(acts, 1):
        if not str(a.get("title") or "").strip() or not str(a.get("what") or "").strip():
            errs.append(f"activity {i} needs 'title' and 'what'")
        try:
            _num(a.get("duration_hours"))
        except (TypeError, ValueError):
            errs.append(f"activity {i}: duration_hours must be a number or '[to confirm]'")
    if not errs:
        errs += check_hours(profile, note) + check_mixups(profile, note)
    return errs


def save(profile, rules, note: dict, target: str = "central") -> dict:
    errs = validate(profile, note)
    if errs:
        raise NoteError("; ".join(errs))
    stamp = f"{note['activity_date']}_{datetime.now():%H%M}"
    topic = slug(note.get("topic") or note["title"])
    if target == "central":
        folder = central_dir(profile) / note["activity_date"][:4] / note["activity_date"][5:7]
        base = f"{stamp}_{slug(note['account'], 3, 20)}_{topic}_activity-note"
    else:
        allowed = {f["path"] for f in account_folders(profile, rules, note["account"])}
        if str(Path(target).expanduser().resolve()) not in allowed:
            raise NoteError("target is not a folder matched to this account; use one of the options "
                            "from targets(), or 'central'")
        folder = Path(target).resolve() / "_ActivityLogging"
        base = f"{stamp}_{topic}_activity-note"
    folder.mkdir(parents=True, exist_ok=True)
    path, i = folder / f"{base}.md", 2
    while path.exists():  # never overwrite
        path, i = folder / f"{base}-{i}.md", i + 1
    path.write_text(render_note(note), encoding="utf-8")
    return {"ok": True, "path": str(path), "target": "central" if target == "central" else "customer_folder"}
