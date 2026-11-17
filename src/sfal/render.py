"""Render the period deliverable from the ledger.

Output layout (documented in docs/reference/output.md):

    <data_dir>/output/<year>/<days|weeks|months|ranges>/<label>/
        Salesforce_Activity_Log_<from>_to_<to>.xlsx   latest - for you (6 sheets)
        Salesforce_Activity_Log_<from>_to_<to>.md     latest - for the AI / quick reading
        runs.md                                       one line per render of this period
        .snapshot.json                                rows of the latest render (for deltas)
        history/                                      earlier versions, timestamped

The folder is chosen from the period's dates (period.classify). Re-rendering with no change
overwrites in place; a changed render first moves the previous version into history/.
Only the latest .xlsx is copied to mirror_to (e.g. ~/Downloads).
"""
from __future__ import annotations

import json
import re
import shutil
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from . import safety
from .ledger import COLUMNS, TO_CONFIRM, Ledger
from .period import classify

SOURCE_NAMES = {"cal": "calendar", "mail": "email", "file": "files", "note": "notes", "imp": "imports", "user": "user"}
LEGACY = re.compile(r"^Salesforce_Activity_Log_(\d{4}-\d{2}-\d{2})_to_(\d{4}-\d{2}-\d{2})\.(md|xlsx)$")


# ---------------------------------------------------------------- data
def period_rows(rows: list[dict], d0: date, d1: date, rules) -> list[dict]:
    out = []
    for r in rows:
        if r["voided"] or not r["activity_date"]:
            continue
        ad = date.fromisoformat(r["activity_date"])
        sd = date.fromisoformat(r["start_date"]) if r["start_date"] else ad
        if d0 <= ad <= d1 or (rules.type_num(r["activity_type"]) in rules.consolidated_types and sd <= d1 and ad >= d0):
            out.append(r)
    return sorted(out, key=lambda r: (r["activity_date"], r["entry_id"]))


def is_held(r: dict) -> bool:
    return (r["activity_hours"] == TO_CONFIRM or r["account_name"] in ("", TO_CONFIRM)
            or r.get("no_opp_reason") == TO_CONFIRM)


def evidence_index(profile) -> dict:
    """id -> {source, date, title} from every cached run."""
    idx = {}
    for f in sorted((profile.data_dir / "cache").glob("*/evidence.json")):
        try:
            for x in json.loads(f.read_text()).get("items", []):
                idx[x["id"]] = {"source": x.get("source"), "date": x.get("date") or "", "title": x.get("title") or ""}
        except (OSError, json.JSONDecodeError):
            continue
    return idx


def _hours(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _h(v) -> str:
    return v if v == TO_CONFIRM else f"{float(v or 0):g}"


def snapshot_rows(rows: list[dict]) -> list[dict]:
    return [{"entry_id": r["entry_id"], "account": r["account_name"], "type": r["activity_type"],
             "date": r["activity_date"], "activity_hours": _hours(r["activity_hours"]),
             "prep_hours": _hours(r["prep_hours"]), "held": is_held(r), "supersedes": r.get("supersedes") or ""}
            for r in rows]


def compute_deltas(before: list[dict] | None, now: list[dict]) -> list[dict]:
    """Per-customer comparison of the previous render of this period with the current one."""
    if before is None:
        return []
    acc = defaultdict(lambda: {"before_h": 0.0, "before_n": 0, "now_h": 0.0, "now_n": 0, "added": [], "removed": []})
    b_ids = {r["entry_id"]: r for r in before}
    n_ids = {r["entry_id"]: r for r in now}
    for r in before:
        a = acc[r["account"]]
        a["before_h"] += r["activity_hours"]
        a["before_n"] += 1
    for r in now:
        a = acc[r["account"]]
        a["now_h"] += r["activity_hours"]
        a["now_n"] += 1
    replaced = {r["supersedes"]: r["entry_id"] for r in now if r["supersedes"] in b_ids}
    for eid, r in n_ids.items():
        if eid not in b_ids and eid not in replaced.values():
            acc[r["account"]]["added"].append(eid)
    for eid, r in b_ids.items():
        if eid not in n_ids and eid not in replaced:
            acc[r["account"]]["removed"].append(eid)
    out = []
    for name, a in sorted(acc.items()):
        details = []
        if a["added"]:
            details.append("added " + ", ".join(a["added"]))
        if a["removed"]:
            details.append("removed " + ", ".join(a["removed"]))
        for old, new in replaced.items():
            if b_ids[old]["account"] == name:
                details.append(f"{old} replaced by {new}")
        change = round(a["now_h"] - a["before_h"], 2)
        status = "new" if a["before_n"] == 0 else "removed" if a["now_n"] == 0 else \
            "changed" if details or change else "unchanged"
        out.append({"account": name, "before_h": round(a["before_h"], 2), "before_n": a["before_n"],
                    "now_h": round(a["now_h"], 2), "now_n": a["now_n"], "change_h": change,
                    "status": status, "details": "; ".join(details)})
    return out


# ---------------------------------------------------------------- folders
def period_folder(profile, d0: date, d1: date) -> tuple[Path, dict]:
    c = classify(d0, d1)
    return profile.data_dir / "output" / c["relpath"], c


def migrate_legacy(profile) -> list[str]:
    """Move files from the old flat output/ layout into their period folder's history/."""
    moved = []
    out = profile.data_dir / "output"
    if not out.exists():
        return moved
    for f in out.iterdir():
        m = LEGACY.match(f.name)
        if not f.is_file() or not m:
            continue
        folder, _ = period_folder(profile, date.fromisoformat(m[1]), date.fromisoformat(m[2]))
        dest = safety.check_writable(profile, folder / "history" / f"{f.stem}_legacy.{m[3]}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(f), dest)
        moved.append(str(dest.relative_to(profile.data_dir)))
    return moved


def _archive_previous(profile, folder: Path, base: str, prev_stamp: str) -> list[str]:
    hist = folder / "history"
    moved = []
    for ext in ("xlsx", "md"):
        f = folder / f"{base}.{ext}"
        if f.exists():
            dest = safety.check_writable(profile, hist / f"{base}_{prev_stamp}.{ext}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), dest)
            moved.append(dest.name)
    return moved


# ---------------------------------------------------------------- markdown
def _cell(s) -> str:
    return str(s if s is not None else "").replace("|", "\\|").replace("\n", " ")


def build_md(ctx: dict) -> str:
    rules, profile = ctx["rules"], ctx["profile"]
    L = [f"# Salesforce Activity Log — {ctx['d0']} to {ctx['d1']}", "",
         f"Owner: **{profile.owner}** · Period type: {ctx['kind']} · Generated {ctx['generated']} · "
         f"Rule pack `{rules.version}` · Timezone `{profile.timezone}`", ""]
    if ctx["sources"]:
        L += [f"Sources used: {', '.join(ctx['sources'])}", ""]
    L += ["## Summary", "",
          f"- Records ready to paste: **{len(ctx['ready'])}** · held (to confirm): **{len(ctx['held'])}**",
          f"- Activity hours: **{ctx['act']:g}** · Prep hours: **{ctx['prep']:g}**", ""]
    if ctx["by_type"]:
        L += ["| Activity type | Records | Activity h |", "|---|---|---|"] + \
             [f"| {t} | {n} | {h:g} |" for t, (n, h) in sorted(ctx["by_type"].items())] + [""]
        L += ["| Account | Records | Activity h |", "|---|---|---|"] + \
             [f"| {a} | {n} | {h:g} |" for a, (n, h) in sorted(ctx["by_acct"].items(), key=lambda kv: -kv[1][1])] + [""]

    L += ["## Paste-Ready (Salesforce form order)", ""]
    if ctx["ready"]:
        L += ["| ID | " + " | ".join(rules.form_fields) + " |", "|" + "---|" * (len(rules.form_fields) + 1)]
        for r in ctx["ready"]:
            L.append(f"| {r['entry_id']} | " + " | ".join(_cell(v) for v in paste_values(r)) + " |")
    else:
        L.append("_No records ready for this period._")
    L.append("")

    L += ["## Changes since previous version", ""]
    if ctx["deltas"] is None:
        L.append("_First version of this period._")
    elif not [d for d in ctx["deltas"] if d["status"] != "unchanged"]:
        L.append("_No changes._")
    else:
        L += ["| Account | Before h | Now h | Change | Details |", "|---|---|---|---|---|"]
        for d in ctx["deltas"]:
            if d["status"] != "unchanged":
                L.append(f"| {d['account']} | {d['before_h']:g} | {d['now_h']:g} | {d['change_h']:+g} | {_cell(d['details'] or d['status'])} |")
    L.append("")

    L += ["## To Confirm (held — not ready to paste)", ""]
    if ctx["held"]:
        L += ["| ID | Date | Account | Type | Activity h | Open questions |", "|---|---|---|---|---|---|"]
        for r in ctx["held"]:
            L.append(f"| {r['entry_id']} | {r['activity_date']} | {_cell(r['account_name'])} | {r['activity_type']} | "
                     f"{_h(r['activity_hours'])} | {_cell(r['to_confirm'])} |")
    else:
        L.append("_Nothing to confirm._")
    L.append("")

    L += ["## Evidence Trail", ""]
    for r in ctx["rows"]:
        L.append(f"- **{r['entry_id']}** {r['account_name']} · {r['activity_type']} ({r['confidence']})")
        for ref in r["evidence_refs"]:
            e = ctx["evidence"].get(ref, {})
            desc = f"{e.get('date', '')} {e.get('title', '')}".strip() or ("(user-confirmed)" if ref.startswith("user:") else "")
            L.append(f"  - `{ref}` {desc}")
    L.append("")
    return "\n".join(L)


def paste_values(r: dict) -> list:
    return [r["account_name"], r["activity_type"], r["opportunity"], r["no_opp_reason"], r["owner"],
            r["status"], r["activity_date"], _h(r["activity_hours"]), _h(r["prep_hours"]),
            r["notes"], "; ".join(r["solution_area"])]


# ---------------------------------------------------------------- excel
def build_xlsx(ctx: dict, path: Path) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    rules, profile = ctx["rules"], ctx["profile"]
    bold = Font(bold=True)
    head_fill = PatternFill("solid", fgColor="DDE7F3")
    wrap = Alignment(wrap_text=True, vertical="top")
    top = Alignment(vertical="top")

    def table(ws, headers, rows, widths=None, start_row=1, wrap_cols=(), freeze=True):
        for j, h in enumerate(headers, 1):
            c = ws.cell(row=start_row, column=j, value=h)
            c.font, c.fill = bold, head_fill
        for i, row in enumerate(rows, start_row + 1):
            for j, v in enumerate(row, 1):
                c = ws.cell(row=i, column=j, value=v)
                c.alignment = wrap if headers[j - 1] in wrap_cols else top
        for j, w in enumerate(widths or [], 1):
            ws.column_dimensions[get_column_letter(j)].width = w
        # Freeze + filter only on single-table sheets. Never set and then unset freeze_panes:
        # openpyxl leaves a selection pointing at the removed pane, which Excel reports as corrupt.
        if freeze:
            if rows:
                ws.auto_filter.ref = f"A{start_row}:{get_column_letter(len(headers))}{start_row + len(rows)}"
            ws.freeze_panes = ws.cell(row=start_row + 1, column=1)

    def num(v):
        return v if v == TO_CONFIRM else _hours(v)

    wb = Workbook()

    # 1 Summary
    ws = wb.active
    ws.title = "Summary"
    info = [("Salesforce Activity Log", f"{ctx['d0']} to {ctx['d1']}"), ("Period type", ctx["kind"]),
            ("Owner", profile.owner), ("Generated", ctx["generated"]), ("Rule pack", rules.version),
            ("Timezone", profile.timezone), ("Sources used", ", ".join(ctx["sources"]) or "-"),
            ("Records ready to paste", len(ctx["ready"])), ("Held (to confirm)", len(ctx["held"])),
            ("Activity hours (ready)", ctx["act"]), ("Prep hours (ready)", ctx["prep"])]
    for i, (k, v) in enumerate(info, 1):
        ws.cell(row=i, column=1, value=k).font = bold
        ws.cell(row=i, column=2, value=v)
    r0 = len(info) + 2
    ws.cell(row=r0, column=1, value="By activity type").font = bold
    rows = [(t, n, h) for t, (n, h) in sorted(ctx["by_type"].items())]
    table(ws, ["Activity type", "Records", "Activity h"], rows, start_row=r0 + 1, freeze=False)
    r1 = r0 + len(rows) + 3
    ws.cell(row=r1, column=1, value="By account").font = bold
    rows = [(a, n, h) for a, (n, h) in sorted(ctx["by_acct"].items(), key=lambda kv: -kv[1][1])]
    table(ws, ["Account", "Records", "Activity h"], rows, widths=[34, 22, 12], start_row=r1 + 1, freeze=False)

    # 2 Paste-Ready
    ws = wb.create_sheet("Paste-Ready")
    rows = []
    for r in ctx["ready"]:
        v = paste_values(r)
        v[7], v[8] = num(r["activity_hours"]), num(r["prep_hours"])
        rows.append([r["entry_id"]] + v)
    table(ws, ["ID"] + list(rules.form_fields), rows,
          widths=[8, 28, 26, 18, 26, 18, 12, 12, 10, 10, 70, 18], wrap_cols=("Activity Hours Notes",))

    # 3 Period Ledger
    ws = wb.create_sheet("Period Ledger")
    rows = []
    for r in ctx["rows"]:
        rows.append([("; ".join(r[c]) if isinstance(r[c], list) else
                      ("true" if r[c] is True else "false" if r[c] is False else
                       num(r[c]) if c in ("activity_hours", "prep_hours") else r[c])) for c in COLUMNS])
    widths = {"notes": 60, "evidence_refs": 30, "account_name": 26, "activity_type": 26, "to_confirm": 30}
    table(ws, COLUMNS, rows, widths=[widths.get(c, 14) for c in COLUMNS], wrap_cols=("notes",))

    # 4 Per-Customer Deltas
    ws = wb.create_sheet("Per-Customer Deltas")
    if ctx["deltas"] is None:
        ws["A1"] = "First version of this period - nothing to compare yet."
    else:
        rows = [(d["account"], d["before_n"], d["before_h"], d["now_n"], d["now_h"], d["change_h"], d["status"], d["details"])
                for d in ctx["deltas"]]
        table(ws, ["Account", "Records before", "Hours before", "Records now", "Hours now", "Change (h)",
                   "Status", "Details"], rows, widths=[28, 14, 12, 12, 10, 11, 11, 50], wrap_cols=("Details",))
        if ctx["prev_generated"]:
            ws.cell(row=len(rows) + 3, column=1, value=f"Compared with the version generated {ctx['prev_generated']}")

    # 5 To-Confirm
    ws = wb.create_sheet("To-Confirm")
    rows = [(r["entry_id"], r["activity_date"], r["account_name"], r["activity_type"], num(r["activity_hours"]),
             r["no_opp_reason"], r["to_confirm"]) for r in ctx["held"]]
    if rows:
        table(ws, ["ID", "Date", "Account", "Type", "Activity h", "No-opp reason", "Open questions"], rows,
              widths=[8, 12, 26, 26, 11, 22, 60], wrap_cols=("Open questions",))
    else:
        ws["A1"] = "Nothing to confirm."

    # 6 Evidence Trail
    ws = wb.create_sheet("Evidence Trail")
    rows = []
    for r in ctx["rows"]:
        for ref in r["evidence_refs"]:
            e = ctx["evidence"].get(ref, {})
            src = SOURCE_NAMES.get(ref.split(":", 1)[0], e.get("source") or "")
            desc = e.get("title") or (ref[5:] if ref.startswith("user:") else "")
            rows.append((r["entry_id"], r["account_name"], r["activity_type"], src, e.get("date", ""), desc, ref))
    table(ws, ["ID", "Account", "Type", "Source", "Evidence date", "Evidence", "Ref"], rows,
          widths=[8, 26, 26, 10, 13, 60, 22], wrap_cols=("Evidence",))

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


# ---------------------------------------------------------------- main
def render(profile, rules, d0: date, d1: date, mirror: bool = True) -> dict:
    migrated = migrate_legacy(profile)
    folder, cls = period_folder(profile, d0, d1)
    safety.check_writable(profile, folder)
    folder.mkdir(parents=True, exist_ok=True)
    base = f"Salesforce_Activity_Log_{d0}_to_{d1}"

    rows = period_rows(Ledger(profile.data_dir).rows(), d0, d1, rules)
    ready = [r for r in rows if not is_held(r)]
    held = [r for r in rows if is_held(r)]
    snap_now = snapshot_rows(rows)

    snap_path = folder / ".snapshot.json"
    prev = json.loads(snap_path.read_text()) if snap_path.exists() else None
    prev_rows = prev["rows"] if prev else None
    deltas = compute_deltas(prev_rows, snap_now)
    changed = prev is None or prev_rows != snap_now
    now = datetime.now()
    archived = []
    if prev and changed:
        archived = _archive_previous(profile, folder, base, prev["stamp"])

    state_p = profile.data_dir / "state.json"
    runs = []
    if state_p.exists():
        runs = [x for x in json.loads(state_p.read_text()).get("runs", [])
                if x.get("from") == d0.isoformat() and x.get("to") == d1.isoformat()]
    sources = (runs[-1].get("sources") if runs else []) or []

    by_type, by_acct = defaultdict(lambda: [0, 0.0]), defaultdict(lambda: [0, 0.0])
    for r in ready:
        for d, k in ((by_type, r["activity_type"]), (by_acct, r["account_name"])):
            d[k][0] += 1
            d[k][1] += _hours(r["activity_hours"])
    ctx = {"profile": profile, "rules": rules, "d0": d0, "d1": d1, "kind": cls["kind"],
           "generated": now.strftime("%Y-%m-%d %H:%M"), "sources": sources,
           "rows": rows, "ready": ready, "held": held,
           "act": round(sum(_hours(r["activity_hours"]) for r in ready), 2),
           "prep": round(sum(_hours(r["prep_hours"]) for r in ready), 2),
           "by_type": {k: tuple(v) for k, v in by_type.items()}, "by_acct": {k: tuple(v) for k, v in by_acct.items()},
           "deltas": deltas if prev else None, "prev_generated": prev.get("generated") if prev else None,
           "evidence": evidence_index(profile)}

    md = safety.write_text(profile, folder / f"{base}.md", build_md(ctx))
    xlsx = safety.check_writable(profile, folder / f"{base}.xlsx")
    build_xlsx(ctx, xlsx)
    snap_path.write_text(json.dumps({"stamp": now.strftime("%Y-%m-%d_%H%M%S"), "generated": ctx["generated"],
                                     "rows": snap_now}, indent=1), encoding="utf-8")

    summary = "first version" if prev is None else ("no change" if not changed else
              "; ".join(f"{d['account']} {d['change_h']:+g}h" + (f" ({d['details']})" if d["details"] else "")
                        for d in deltas if d["status"] != "unchanged"))
    runs_md = folder / "runs.md"
    if not runs_md.exists():
        safety.write_text(profile, runs_md, f"# Runs — {d0} to {d1} ({cls['kind']})\n\n"
                          "| Rendered | Committed runs | Records | Activity h | Changes |\n|---|---|---|---|---|\n")
    committed = ", ".join(x["run_id"] for x in runs if x.get("committed")) or "-"
    with open(runs_md, "a", encoding="utf-8") as f:
        f.write(f"| {ctx['generated']} | {committed} | {len(rows)} | {ctx['act']:g} | {_cell(summary)} |\n")

    mirrored = safety.mirror(profile, xlsx) if mirror else None
    return {"folder": str(folder), "period_type": cls["kind"], "xlsx": str(xlsx), "md": str(md),
            "mirrored_to": str(mirrored) if mirrored else None, "ready": len(ready), "held": len(held),
            "activity_hours": ctx["act"], "prep_hours": ctx["prep"], "changes": summary,
            "archived_previous": archived, "migrated_legacy_files": migrated}
