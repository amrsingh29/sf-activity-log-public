"""Setup: propose a profile from the user's own data, then save the confirmed version.

scan()          deterministic discovery - folder structure, account-folder candidates,
                calendar and sent-mail domains, likely personal blocks, owner identity.
                Proposes; never writes.
save_profile()  validates a profile dict and writes ~/.sf-activity-log/profile.yaml
                (previous file kept as profile.yaml.bak-<timestamp>).

The AI runs the interview in between: it shows the scan, asks the user to confirm accounts,
partners, sources and blocks, and builds the profile dict.
"""
from __future__ import annotations

import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

from .profile import DEFAULTS, ProfileError, _merge, load_profile, profile_path, validate

REGIONS = {
    "singapore", "malaysia", "thailand", "vietnam", "indonesia", "philippines", "india", "australia",
    "newzealand", "new zealand", "nz", "hongkong", "hong kong", "hk", "dubai", "uae", "saudi", "qatar",
    "japan", "korea", "china", "taiwan", "apac", "asean", "anz", "emea", "americas", "na", "latam",
    "europe", "uk", "germany", "france", "usa", "us", "canada", "brazil", "mexico", "middle east",
}
NOISE_TOKENS = re.compile(
    r"(?i)\b(20\d\d|rfp|rfi|rft|poc|pov|tender|itsm|itom|esm|bwf|aiops|helix|migration|discovery|"
    r"renewal|upgrade|project|proposal|demo|workshop|setup|presentation|ppt)\b")
SKIP = re.compile(r"^[._~]")


def _clean_name(folder: str) -> str:
    s = re.sub(r"[_\-]+", " ", folder)
    s = NOISE_TOKENS.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip(" -_")
    return s or folder


def scan_folders(root: Path) -> dict:
    all_dirs = sorted(d.name for d in root.iterdir() if d.is_dir() and not d.name.startswith("."))
    level1 = [n for n in all_dirs if not SKIP.match(n)]
    regional = [n for n in level1 if n.lower() in REGIONS]
    level = 2 if len(regional) >= max(1, len(level1) // 2) else 1
    candidates = []
    parents = [root / r for r in regional] if level == 2 else [root]
    for parent in parents:
        for d in sorted(parent.iterdir()):
            if not d.is_dir() or SKIP.match(d.name):
                continue
            try:
                children = sum(1 for _ in d.iterdir())
                mtime = datetime.fromtimestamp(d.stat().st_mtime).date().isoformat()
            except OSError:
                children, mtime = 0, None
            candidates.append({"folder": str(d.relative_to(root)), "name": d.name,
                               "suggested_account": _clean_name(d.name), "items": children, "modified": mtime})
    other = [n for n in level1 if n not in regional] if level == 2 else []
    return {"root": str(root), "level1": level1, "regional_folders": regional,
            "suggested_account_folder_level": level, "account_folder_candidates": candidates,
            "non_regional_top_folders": other,
            "suggested_notes_save_to": "customer_folder" if len(candidates) >= 5 else "central",
            "suggested_internal_folders": [n for n in all_dirs if "internal" in n.lower()],
            "system_folders_skipped": [n for n in all_dirs if SKIP.match(n)]}


def _domain(e: str) -> str:
    return e.rsplit("@", 1)[-1].lower() if "@" in (e or "") else ""


def scan_calendar(days: int, source: str | None) -> dict:
    from .sources import calendar as cal
    d1 = date.today()
    raw = cal.fetch(d1 - timedelta(days=days), d1, source)
    owner = Counter()
    for e in raw["events"]:
        org = e.get("organizer") or {}
        if org.get("is_me") and org.get("email"):
            owner[(org.get("name") or "", org["email"].lower())] += 1
        for a in e.get("attendees", []):
            if a.get("is_me") and a.get("email"):
                owner[(a.get("name") or "", a["email"].lower())] += 1
    me = owner.most_common(1)[0][0] if owner else ("", "")
    my_domain = _domain(me[1])
    # Your other addresses: attendees carrying your name but not flagged as you.
    aliases = Counter(a["email"].lower() for e in raw["events"] for a in e.get("attendees", [])
                      if me[0] and (a.get("name") or "").strip().lower() == me[0].lower()
                      and a.get("email") and a["email"].lower() != me[1])
    mine = {me[1]} | set(aliases)
    my_domains = {my_domain} | {_domain(a) for a in aliases}
    domains, titles = Counter(), defaultdict(list)
    solo = Counter()
    for e in raw["events"]:
        if e.get("all_day") or e.get("cancelled"):
            continue
        others = [a for a in e.get("attendees", []) if not a.get("is_me") and a.get("email", "").lower() not in mine]
        if not others:
            solo[(e.get("title") or "").strip()] += 1
        for d in {_domain(a.get("email", "")) for a in others} - {""} - my_domains:
            domains[d] += 1
            if len(titles[d]) < 3 and e.get("title") not in titles[d]:
                titles[d].append(e.get("title"))
    return {"events": len(raw["events"]), "available_sources": raw.get("available_sources"),
            "owner_guess": {"name": me[0], "email": me[1], "domain": my_domain,
                            "aliases": [a for a, _ in aliases.most_common(5)],
                            "suggested_email_domains": sorted(my_domains - {""})},
            "external_domains": [{"domain": d, "meetings": n, "sample_titles": titles[d]}
                                 for d, n in domains.most_common(40)],
            "likely_personal_blocks": [{"title": t, "count": n} for t, n in solo.most_common(15) if n >= 3 and t]}


def scan_email(days: int, account: str, my_domains: set[str]) -> dict:
    from .sources import email as em
    d1 = date.today()
    raw = em.fetch_mailbox(account, "Sent Items", d1 - timedelta(days=days), d1, preview=0)
    domains, subjects = Counter(), defaultdict(list)
    for m in raw["messages"]:
        for a in m["to"] + m["cc"]:
            d = _domain(em._addr(a))
            if d and d not in my_domains:
                domains[d] += 1
                if len(subjects[d]) < 3:
                    subjects[d].append(em.thread_subject(m["subject"]))
    return {"sent_messages": len(raw["messages"]), "oldest_synced": raw["oldest"],
            "external_domains": [{"domain": d, "messages": n, "sample_subjects": subjects[d]}
                                 for d, n in domains.most_common(40)]}


def _progress(msg: str) -> None:
    """Progress goes to stderr so stdout stays clean JSON for the AI and scripts."""
    print(f"[setup-scan] {msg}", file=sys.stderr, flush=True)


def scan(root: str | None = None, days: int = 60, profile: str | None = None,
         calendar_source: str = "Exchange", mail_account: str = "Exchange") -> dict:
    started = time.monotonic()
    existing = None
    try:
        existing = load_profile(profile)
    except ProfileError:
        pass
    out: dict = {"ok": True, "profile_path": str(profile_path(profile)),
                 "existing_profile": existing.data if existing else None, "days_scanned": days, "warnings": []}
    root_p = Path(os.path.expanduser(root)) if root else (existing.workspace_root if existing else None)
    if root_p and root_p.exists():
        _progress(f"scanning folders under {root_p} (large folders can take a minute)...")
        out["folders"] = scan_folders(root_p)
        _progress(f"folders done: {len(out['folders'].get('account_folder_candidates', []))} customer folder candidates")
    else:
        out["warnings"].append("no workspace root given/found - ask the user for their customer folder")
    _progress(f"reading calendar, last {days} days (the first run compiles a small helper, so it is slower)...")
    try:
        out["calendar"] = scan_calendar(days, calendar_source)
        _progress(f"calendar done: {out['calendar'].get('events', 0)} events")
    except Exception as e:
        out["warnings"].append(f"calendar scan failed: {e}")
    my = set(out.get("calendar", {}).get("owner_guess", {}).get("suggested_email_domains") or [])
    if existing:
        my |= set(existing.internal_domains)
    _progress(f"reading sent mail, last {days} days...")
    try:
        out["email"] = scan_email(days, mail_account, my)
        _progress("mail done")
    except Exception as e:
        out["warnings"].append(f"email scan failed: {e}")
    _progress(f"scan finished in {time.monotonic() - started:.0f}s")
    return out


def save_profile(data: dict, profile: str | None = None) -> dict:
    """Validate and write the profile. Only this path is written."""
    if not isinstance(data, dict):
        raise ProfileError("profile must be an object")
    merged = _merge(DEFAULTS, data)
    errs = validate(merged)
    if errs:
        raise ProfileError("profile invalid:\n  - " + "\n  - ".join(errs))
    dest = profile_path(profile)
    dest.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if dest.exists():
        backup = dest.with_name(f"{dest.name}.bak-{datetime.now():%Y%m%d-%H%M%S}")
        dest.rename(backup)
    header = ("# SF Activity Log - personal profile (written by setup).\n"
              "# Edit freely; reference: docs/reference/configuration.md\n\n")
    dest.write_text(header + yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    Path(os.path.expanduser(str(merged["data_dir"]))).mkdir(parents=True, exist_ok=True)
    return {"ok": True, "profile": str(dest), "backup": str(backup) if backup else None,
            "next": "run doctor to check access to the enabled sources"}
