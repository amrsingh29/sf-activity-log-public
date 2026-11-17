"""Calendar source - macOS EventKit via a small compiled Swift helper (read-only)."""
from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import subprocess
from datetime import date, datetime
from pathlib import Path

from ..evidence import item, make_id

HELPER_SRC = Path(__file__).resolve().parent.parent / "helpers" / "eventkit_dump.swift"
BIN_DIR = Path("~/.sf-activity-log/bin").expanduser()
CANCEL_PREFIXES = ("canceled:", "cancelled:")
PEOPLE_LIMIT = 12


class CalendarError(Exception):
    pass


def helper_path() -> Path:
    """Compile the Swift helper once per source revision; reuse the binary afterwards."""
    digest = hashlib.sha1(HELPER_SRC.read_bytes()).hexdigest()[:10]
    exe = BIN_DIR / f"eventkit_dump-{digest}"
    if exe.exists():
        return exe
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["swiftc", "-O", str(HELPER_SRC), "-o", str(exe)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise CalendarError(f"could not compile EventKit helper (is Xcode CLT installed?):\n{r.stderr[-800:]}")
    for old in BIN_DIR.glob("eventkit_dump-*"):
        if old != exe:
            old.unlink(missing_ok=True)
    return exe


def fetch(d0: date, d1: date, source: str | None) -> dict:
    cmd = [str(helper_path()), "--from", d0.isoformat(), "--to", d1.isoformat()]
    if source:
        cmd += ["--source", source]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    try:
        out = json.loads(r.stdout)
    except json.JSONDecodeError:
        raise CalendarError(f"EventKit helper failed: {r.stderr[-500:] or r.stdout[-500:]}") from None
    if out.get("status") != "ok":
        raise CalendarError(out.get("message") or out.get("status"))
    return out


def _domain(email: str) -> str:
    return email.rsplit("@", 1)[-1].lower() if "@" in (email or "") else ""


def _has_kw(title: str, keywords) -> bool:
    t = title.lower()
    return any(k.lower() in t for k in keywords or [])


TEAMS_NOISE = re.compile(r"(?is)_{5,}.*?(microsoft teams|join the meeting|meeting id).*$")


def _clean_invite(text: str) -> str:
    """Invite description without the Teams/Zoom join boilerplate at the end."""
    t = TEAMS_NOISE.sub("", text or "")
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()[:4000]


def normalize(raw: dict, profile, rules) -> list[dict]:
    cfg = profile.source("calendar")
    ignore = [p.lower() for p in cfg.get("ignore_titles") or []]
    threshold = int(cfg.get("broadcast_threshold") or 40)
    internal = set(profile.internal_domains)

    items = []
    for i, e in enumerate(raw["events"]):
        title = (e.get("title") or "").strip()
        start = datetime.fromisoformat(e["start"])
        end = datetime.fromisoformat(e["end"])
        hours = round((end - start).total_seconds() / 3600, 2)
        others = [a for a in e.get("attendees", [])
                  if not profile.is_me(a.get("name"), a.get("email"), a.get("is_me"))]
        org = e.get("organizer", {})
        org_is_me = profile.is_me(org.get("name"), org.get("email"), org.get("is_me"))
        emails = [a.get("email", "") for a in others] + ([] if org_is_me else [org.get("email", "")])
        domains = sorted({_domain(m) for m in emails if _domain(m)})
        external = [d for d in domains if d not in internal]

        my_status = e.get("my_status") or "none"
        flags = []
        excluded = None
        tl = title.lower()
        if e.get("cancelled") or tl.startswith(CANCEL_PREFIXES):
            excluded = "cancelled"
        elif my_status == "declined":
            excluded = "declined"
        elif e.get("all_day"):
            excluded = "all_day"
        elif any(fnmatch.fnmatch(tl, p) for p in ignore):
            excluded = "ignored_title"

        if len(e.get("attendees", [])) > threshold:
            flags.append("broadcast")
        if my_status in ("unknown", "none", "pending") and not org_is_me:
            flags.append("rsvp_unknown")
        if my_status == "tentative":
            flags.append("tentative")
        if not others:
            flags.append("solo")
        if domains and not external:
            flags.append("internal_only")
        if _has_kw(title, rules.prep_title_keywords):
            flags.append("prep_title")
        if _has_kw(title, rules.demo_title_keywords):
            flags.append("demo_title")
        if e.get("recurring"):
            flags.append("recurring")

        items.append(item(
            id=make_id("cal", e.get("external_id", ""), e["start"]),
            source="calendar", kind="meeting",
            date=start.date().isoformat(), start=e["start"], end=e["end"],
            hours=None if e.get("all_day") else hours,
            title=title,
            people=[a.get("name") or a.get("email") for a in others][:PEOPLE_LIMIT],
            domains=external,
            flags=flags, excluded=excluded,
            attendee_count=len(e.get("attendees", [])),
            organizer="me" if org_is_me else (org.get("name") or ""),
            my_status=my_status,
            location=e.get("location") or "",
            timezone=e.get("timezone"),
            # full detail for /log-activity-note (kept in the run cache, not sent to the weekly AI step)
            description=_clean_invite(e.get("notes") or ""),
            attendees=[{"name": a.get("name") or a.get("email"), "status": a.get("status"),
                        "domain": _domain(a.get("email", ""))} for a in others][:40],
            organizer_name="me" if org_is_me else (org.get("name") or ""),
            raw_ref=f"calendar.json#events[{i}]",
        ))

    _mark_overlaps(items)
    return items


def _mark_overlaps(items: list[dict]) -> None:
    live = sorted((x for x in items if not x["excluded"] and x["start"]), key=lambda x: x["start"])
    for a_i, a in enumerate(live):
        a_end = datetime.fromisoformat(a["end"])
        for b in live[a_i + 1:]:
            if datetime.fromisoformat(b["start"]) >= a_end:
                break
            a.setdefault("overlaps", []).append(b["id"])
            b.setdefault("overlaps", []).append(a["id"])
    for x in live:
        if x.get("overlaps"):
            x["flags"].append("overlap")


def collect(profile, rules, d0: date, d1: date, raw_dir: Path):
    cfg = profile.source("calendar")
    raw = fetch(d0, d1, cfg.get("eventkit_source"))
    (raw_dir / "calendar.json").write_text(json.dumps(raw, indent=1), encoding="utf-8")
    items = normalize(raw, profile, rules)
    report = {
        "source": "calendar", "method": "eventkit",
        "events": len(items),
        "excluded": sum(1 for x in items if x["excluded"]),
        "kept": sum(1 for x in items if not x["excluded"]),
        "completeness": "complete",
    }
    return items, report
