"""Stages 1-3: resolve period, collect evidence from enabled sources, pre-classify.

Output: cache/<run_id>/evidence.json and candidates.json. Deterministic - no AI here.

Cross-source steps (after every source has been collected):
  1. account matching against the registry (all text of each item + domains + folder)
  2. RSVP emails -> confirm / contradict calendar attendance
  3. imported meetings that duplicate a calendar meeting -> merged (calendar wins)
  4. file work sessions -> linked to nearby activities of the same account (prep / follow-up),
     otherwise flagged `gap` = possible unlogged work
  5. dedupe against the ledger
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from . import decisions as dec
from .accounts import Registry
from .ledger import Ledger
from .sources import calendar as src_calendar
from .sources import email as src_email
from .sources import files as src_files
from .sources import imports as src_imports
from .sources import notes as src_notes

# Sources implemented in the engine. gbrain is consulted by the AI host via MCP.
ENGINE_SOURCES = {"calendar": src_calendar, "email": src_email, "files": src_files,
                  "notes": src_notes, "imports": src_imports}
HOST_SOURCES = {"gbrain"}
ALL_SOURCES = ("calendar", "email", "files", "notes", "imports", "gbrain")
ACTIVITY_KINDS = ("meeting", "email", "note", "other")


def new_run_id(d0: date, d1: date) -> str:
    return f"{d0:%Y%m%d}-{d1:%Y%m%d}_{datetime.now():%H%M%S}"


def run_dir(profile, run_id: str) -> Path:
    return profile.data_dir / "cache" / run_id


def open_records(ledger_rows: list[dict], rules) -> list[dict]:
    """Active consolidated records (RFP/Value Review/POC) that new evidence may extend."""
    out = []
    for r in ledger_rows:
        if rules.type_num(r["activity_type"]) in rules.consolidated_types and r["status"] in ("In Progress", "Planned"):
            out.append({k: r[k] for k in ("entry_id", "account_name", "activity_type", "consolidation_key",
                                          "start_date", "activity_date", "activity_hours", "prep_hours", "status")})
    return out


def _words(t: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (t or "").lower()) if len(w) > 2}


def _similar(a: str, b: str) -> float:
    wa, wb = _words(a), _words(b)
    return len(wa & wb) / len(wa | wb) if wa and wb else 0.0


# ---------------------------------------------------------------- cross-source steps
def match_accounts(items: list[dict], registry: Registry, internal_folders: list[str]) -> None:
    for x in items:
        if x["excluded"]:
            continue
        texts = [x["title"], x.get("location", ""), x.get("account_text", "")] + list(x.get("path_texts") or []) \
            + list(x.get("attachments") or [])
        folder = x.get("folder") or ""
        in_internal = any(folder == f or folder.startswith(f + "/") for f in internal_folders)
        declared = registry.canonical(x.get("declared_account") or "")
        if declared:  # a note that names its account is trusted over any guess
            x["account_hint"] = {"name": declared, "kind": registry.kind_of(declared),
                                 "via": ["note:account"], "certain": True}
            continue
        x["account_hint"] = registry.match(
            texts, x["domains"], folder_hint=folder or None,
            internal_only=in_internal or "internal_only" in x["flags"] or "solo" in x["flags"])


def apply_rsvps(items: list[dict]) -> None:
    """An RSVP email applies to the calendar occurrence on its date, or the next one after it."""
    rsvps = [x for x in items if x["kind"] == "rsvp"]
    meetings = sorted((x for x in items if x["source"] == "calendar" and not x["excluded"]),
                      key=lambda x: x["start"] or "")
    for r in sorted(rsvps, key=lambda x: x["date"]):
        target = next((m for m in meetings if m["date"] >= r["date"]
                       and _similar(m["title"], r["rsvp_subject"]) >= 0.8), None)
        if not target:
            continue
        if r["rsvp"] in ("accepted", "tentative", "tentatively accepted"):
            target["flags"] = [f for f in target["flags"] if f != "rsvp_unknown"] + [f"{r['rsvp'].split()[0]}_by_email"]
        elif r["rsvp"] == "declined":
            target["flags"] = [f for f in target["flags"] if f != "rsvp_unknown"] + ["declined_by_email"]
        target.setdefault("rsvp_refs", []).append(r["id"])


def dedupe_imports(items: list[dict]) -> int:
    cal = [x for x in items if x["source"] == "calendar" and not x["excluded"]]
    n = 0
    for x in items:
        if x["source"] != "imports" or x["excluded"] or x["kind"] != "meeting":
            continue
        dup = next((c for c in cal if c["date"] == x["date"] and _similar(c["title"], x["title"]) >= 0.6), None)
        if dup:
            x["excluded"] = f"duplicate_of:{dup['id']}"
            n += 1
    return n


def link_files(items: list[dict], ledger_rows: list[dict], window_days: int) -> None:
    acts = [x for x in items if x["kind"] in ACTIVITY_KINDS and not x["excluded"]
            and x["source"] != "files" and (x.get("account_hint") or {}).get("name")]
    for f in items:
        if f["source"] != "files" or f["excluded"]:
            continue
        acct = (f.get("account_hint") or {}).get("name")
        if not acct:
            f["flags"].append("gap")
            continue
        fd = date.fromisoformat(f["date"])
        links = []
        for a in acts:
            if a["account_hint"]["name"] != acct:
                continue
            delta = (date.fromisoformat(a["date"]) - fd).days
            if 0 <= delta <= window_days:
                links.append({"id": a["id"], "as": "prep_for", "days": delta})
            elif -window_days <= delta < 0:
                links.append({"id": a["id"], "as": "follow_up_of", "days": -delta})
        for r in ledger_rows:
            if r["account_name"] == acct and r["activity_date"] and \
                    abs((date.fromisoformat(r["activity_date"]) - fd).days) <= window_days:
                links.append({"entry_id": r["entry_id"], "as": "near_logged_activity"})
        if links:
            f["links"] = links
            f["flags"].append("supports_activity")
        else:
            f["flags"].append("gap")


# ---------------------------------------------------------------- main
def prepare(profile, rules, d0: date, d1: date, only=None, without=None) -> dict:
    sources = profile.enabled_sources(only, without)
    run_id = new_run_id(d0, d1)
    rd = run_dir(profile, run_id)
    (rd / "raw").mkdir(parents=True, exist_ok=True)

    registry = Registry(profile.accounts, rules.internal_account)
    ledger = Ledger(profile.data_dir)
    active = ledger.active()
    logged = {ref: r["entry_id"] for r in active for ref in r["evidence_refs"]}

    items, reports, warnings = [], [], []
    for s in sources:
        if s in HOST_SOURCES:
            reports.append({"source": s, "method": "host (AI via MCP)", "note": "context only, never dates/hours"})
            continue
        try:
            got, rep = ENGINE_SOURCES[s].collect(profile, rules, d0, d1, rd / "raw")
        except Exception as e:  # report and continue with other sources
            warnings.append(f"source '{s}' failed: {e}")
            reports.append({"source": s, "error": str(e)})
            continue
        items.extend(got)
        reports.append(rep)
        warnings += [f"{s}: {w}" for w in rep.get("warnings", [])]

    match_accounts(items, registry, profile.data["workspace"].get("internal_folders") or [])
    apply_rsvps(items)
    merged = dedupe_imports(items)
    link_files(items, active, int(profile.source("files").get("link_window_days") or 3))
    for x in items:
        if not x["excluded"]:
            hit = next((logged[i] for i in [x["id"]] + list(x.get("legacy_ids") or []) if i in logged), None)
            if hit:                                   # a moved note matches the record logged before the move
                x["logged_as"] = hit

    disabled = [s for s in ALL_SOURCES if s not in sources]
    evidence = {"run_id": run_id, "period": {"from": d0.isoformat(), "to": d1.isoformat()},
                "timezone": profile.timezone, "sources_used": sources, "sources_disabled": disabled,
                "reports": reports, "warnings": warnings, "items": items}
    (rd / "evidence.json").write_text(json.dumps(evidence, indent=1, ensure_ascii=False, default=str), encoding="utf-8")

    live = [x for x in items if not x["excluded"]]
    fresh = [x for x in live if not x.get("logged_as")]
    new_ev = [_compact(x) for x in fresh if x["source"] != "files"]
    file_work = [_compact(x) for x in fresh if x["source"] == "files"]
    live_ids = {i for x in live for i in [x["id"]] + list(x.get("legacy_ids") or [])}  # incl. ids before a move
    logged_rows = [r for r in active if r["evidence_refs"] and any(ref in live_ids for ref in r["evidence_refs"])]
    decisions = dec.build(new_ev, file_work)
    candidates = {
        "run_id": run_id,
        "period": evidence["period"],
        "sources_used": sources,
        "sources_disabled": disabled,
        "warnings": warnings,
        "source_reports": [{k: v for k, v in r.items() if k not in ("files", "warnings")} for r in reports],
        "excluded_summary": dict(Counter(x["excluded"].split(":")[0] for x in items if x["excluded"])),
        "imports_merged_into_calendar": merged,
        "already_logged": [{"id": x["id"], "entry_id": x["logged_as"], "title": x["title"]}
                           for x in live if x.get("logged_as")],
        "already_logged_summary": {   # engine totals - quote these, never add up hours yourself
            "records": len(logged_rows),
            "activity_hours": round(sum(r["activity_hours"] for r in logged_rows
                                        if isinstance(r["activity_hours"], float)), 2),
            "prep_hours": round(sum(r["prep_hours"] for r in logged_rows if isinstance(r["prep_hours"], float)), 2),
            "entries": [{"entry_id": r["entry_id"], "date": r["activity_date"], "account": r["account_name"],
                         "type": r["activity_type"], "hours": r["activity_hours"]} for r in logged_rows]},
        "new_evidence": new_ev,
        "file_work": file_work,
        "decisions": decisions,
        "decisions_text": dec.compact_table(decisions),
        "possible_unlogged_work": [x["id"] for x in fresh if x["source"] == "files" and "gap" in x["flags"]],
        "open_records": open_records(active, rules),
    }
    (rd / "candidates.json").write_text(json.dumps(candidates, indent=1, ensure_ascii=False, default=str),
                                        encoding="utf-8")
    _write_state(profile, run_id, d0, d1, sources)
    return candidates


COMPACT_KEYS = ("id", "source", "kind", "date", "start", "end", "hours", "title", "people", "domains",
                "account_hint", "flags", "attendee_count", "organizer", "my_status", "overlaps", "completeness",
                "message_count", "attachments", "preview", "mailboxes", "folder", "file_count", "links",
                "note_created", "quote", "account_text")


def _compact(x: dict) -> dict:
    out = {k: x.get(k) for k in COMPACT_KEYS if x.get(k) not in (None, [], "")}
    if x.get("files"):
        out["files"] = [{"name": f["file"].rsplit("/", 1)[-1], "signal": f["signal"], "new": f["created"],
                         **({"title": f["title"]} if f.get("title") else {})} for f in x["files"]]
    if out.get("preview"):
        out["preview"] = out["preview"][:240]
    return out


def _write_state(profile, run_id, d0, d1, sources):
    p = profile.data_dir / "state.json"
    state = json.loads(p.read_text()) if p.exists() else {"runs": []}
    state["runs"].append({"run_id": run_id, "from": d0.isoformat(), "to": d1.isoformat(),
                          "sources": sources, "prepared_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                          "committed": False})
    p.write_text(json.dumps(state, indent=1), encoding="utf-8")
