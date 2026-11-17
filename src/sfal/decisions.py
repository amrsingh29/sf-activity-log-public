"""Decisions the user must make, built by the engine (not the AI) from evidence flags.

Each decision has short options and a suggested default, so every host can ask the same
questions the same way: OpenCode's question tool, Goose via MCP elicitation (sfal_ask), or a
compact one-line list. Items with no flag needing input are not decisions; the AI proposes them.
"""
from __future__ import annotations

from datetime import datetime

LOG, SKIP, OTHER_HOURS = "Log", "Skip", "Hours"   # Hours = log it with the hours the user gives


def _when(x: dict) -> str:
    d = datetime.fromisoformat(x["date"]) if x.get("date") else None
    s = d.strftime("%a %d %b") if d else ""
    if x.get("start"):
        s += " " + x["start"][11:16]
    return s


def _reason_and_default(x: dict) -> tuple[str, list[str], str] | None:
    f = set(x.get("flags") or [])
    internal = (x.get("account_hint") or {}).get("kind") in (None, "internal")
    timed = [SKIP, LOG, OTHER_HOURS]
    if "declined_by_email" in f:
        return "declined by email", timed, SKIP
    if x["source"] == "calendar" and x.get("my_status") == "none" and "solo" not in f:
        return "not on the invite", timed, SKIP
    if "broadcast" in f:
        return f"broadcast ({x.get('attendee_count')} invited)", timed, SKIP
    if "overlap" in f:
        return "overlaps another meeting", timed, SKIP if internal else LOG
    if "tentative" in f:
        return "RSVP tentative", timed, SKIP if internal else LOG
    if "rsvp_unknown" in f:
        return "no RSVP on record", timed, SKIP if internal else LOG
    if x["source"] == "email":
        return "email only, hours unknown", [SKIP, OTHER_HOURS], SKIP if internal else OTHER_HOURS
    if x["source"] in ("notes", "imports") and not x.get("hours"):
        return "hours not stated", [SKIP, OTHER_HOURS], OTHER_HOURS
    if x["source"] == "files" and "gap" in f:
        return "file work, nothing logged", [SKIP, OTHER_HOURS], SKIP
    return None


def build(new_evidence: list[dict], file_work: list[dict]) -> list[dict]:
    out = []
    for x in new_evidence + [f for f in file_work if "gap" in (f.get("flags") or [])]:
        r = _reason_and_default(x)
        if not r:
            continue
        reason, options, default = r
        acct = (x.get("account_hint") or {}).get("name") or "account?"
        out.append({"n": len(out) + 1, "id": x["id"], "when": _when(x), "hours": x.get("hours"),
                    "title": x.get("title", "")[:70], "account": acct, "reason": reason,
                    "options": options, "default": default})
    return out


def compact_table(decisions: list[dict]) -> str:
    """Plain-text table that reads well in any terminal (no Markdown needed)."""
    if not decisions:
        return ""
    lines = [f'Needs your call ({len(decisions)}) - reply "ok" to accept all defaults, '
             'or e.g. "1 log, 5 hours 1h, 6 skip"  (hours = log with the hours you give)', ""]
    for d in decisions:
        h = f'{d["hours"]:g}h' if d.get("hours") else "  - "
        lines.append(f'{d["n"]:>2}  {d["when"]:<16} {h:>5}  {d["title"][:40]:<40}  {d["reason"][:26]:<26} -> {d["default"]}')
    return "\n".join(lines)
