"""Engine operations as plain functions returning dicts.

Shared by the CLI (`sfal`) and the MCP server (`sfal-mcp`), so every host gets identical
behaviour. Functions raise ApiError for user/validation problems; the caller formats it.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from . import __version__
from .ledger import Ledger
from .period import classify, resolve
from .prepare import prepare as _prepare
from .prepare import run_dir
from .profile import ProfileError, load_profile, profile_path
from .render import period_rows
from .render import render as _render
from .rules import load_rules
from .safety import check_writable
from .validate import Validator, approval_code

SOURCES = ("calendar", "email", "files", "notes", "imports", "gbrain")


class ApiError(Exception):
    def __init__(self, message: str, **extra):
        super().__init__(message)
        self.extra = extra


def _ctx(profile: str | None = None):
    p = load_profile(profile)
    return p, load_rules(p.data.get("rules_pack"))


def _run(p, run_id: str) -> tuple[Path, dict]:
    rd = run_dir(p, run_id)
    if not (rd / "evidence.json").exists():
        raise ApiError(f"run {run_id} not found (expected {rd})")
    return rd, json.loads((rd / "evidence.json").read_text())


def _proposal(rd: Path, path: str | None = None) -> dict:
    f = Path(path) if path else rd / "proposal.json"
    if not f.exists():
        raise ApiError(f"proposal not found: {f}")
    return json.loads(f.read_text())


def review_table(proposal: dict, result: dict) -> str:
    errs = {}
    for e in result["errors"] + result["warnings"]:
        errs.setdefault(e["change"], []).append(f'{e["code"]}: {e["message"]}')
    L = ["| # | Action | Date | Account | Type | Act h | Prep h | Status | Evidence | To confirm | Issues |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, c in enumerate(proposal.get("changes", [])):
        r = c.get("row") or {}
        act = c["action"] + (f' {c.get("supersedes")}' if c.get("supersedes") else "") + \
            (f' {c.get("entry_id")}' if c["action"] == "void" else "")
        cells = [str(i), act, r.get("activity_date", ""), r.get("account_name", ""), r.get("activity_type", ""),
                 str(r.get("activity_hours", "")), str(r.get("prep_hours", "")), r.get("status", ""),
                 str(len(r.get("evidence_refs") or [])), r.get("to_confirm", ""), "; ".join(errs.get(i, []))]
        L.append("| " + " | ".join(str(x).replace("|", "\\|") for x in cells) + " |")
    return "\n".join(L)


# ---------------------------------------------------------------- operations
def doctor(profile: str | None = None) -> dict:
    report = {"version": __version__, "profile_path": str(profile_path(profile))}
    try:
        p = load_profile(profile)
    except ProfileError as e:
        return {**report, "ok": False, "profile": str(e),
                "next": "run the setup flow (setup_scan + setup_save_profile) or `sfal profile init`"}
    try:
        rules = load_rules(p.data.get("rules_pack"))
    except ProfileError as e:
        return {**report, "ok": False, "rules_pack": str(e), "next": "fix or remove rules_pack in your profile"}
    report.update({"owner": p.owner, "data_dir": str(p.data_dir), "rule_pack": rules.version,
                   "enabled_sources": [s for s in SOURCES if p.source(s).get("enabled")]})
    checks = {}
    if p.source("calendar").get("enabled"):
        from .sources import calendar as cal
        try:
            raw = cal.fetch(date.today(), date.today(), p.source("calendar").get("eventkit_source"))
            checks["calendar"] = {"ok": True, "events_today": len(raw["events"]),
                                  "available_sources": raw.get("available_sources")}
        except Exception as e:
            checks["calendar"] = {"ok": False, "error": str(e)}
    if p.source("email").get("enabled"):
        from .sources import email as em
        cfg = p.source("email")
        for mb in cfg.get("mailboxes") or ["Sent Items"]:
            try:
                got = em.fetch_mailbox(cfg.get("account") or "Exchange", mb, date.today(), date.today(), preview=0)
                checks[f"email:{mb}"] = {"ok": True, "messages_today": len(got["messages"]),
                                         "oldest_synced": got["oldest"]}
            except Exception as e:
                checks[f"email:{mb}"] = {"ok": False, "error": str(e)}
    for s in ("files", "notes"):
        if p.source(s).get("enabled"):
            root = p.workspace_root
            checks[s] = {"ok": bool(root and root.exists()), "workspace_root": str(root)}
    if p.source("imports").get("enabled"):
        inbox = p.data_dir / "inbox"
        checks["imports"] = {"ok": True, "inbox": str(inbox),
                             "files": len([f for f in inbox.glob("*") if f.is_file()]) if inbox.exists() else 0}
    report["checks"] = checks
    report["ok"] = all(c.get("ok") for c in checks.values())
    return report


def rules(profile: str | None = None) -> dict:
    try:
        pack = load_profile(profile).data.get("rules_pack")
    except ProfileError:
        pack = None   # no profile yet: show the bundled pack
    r = load_rules(pack)
    return {"version": r.version, "internal_account": r.internal_account, "statuses": r.statuses,
            "solution_areas": r.solution_areas, "routing": r.routing,
            "activity_types": [{"code": f'{t["num"]} · {t["name"]}', "definition": t["definition"]}
                               for t in r.activity_types],
            "consolidated_types": r.consolidated_types, "deal_types": r.deal_types,
            "partner_enablement_types": r.partner_enablement_types}


def profile_show(profile: str | None = None) -> dict:
    p = load_profile(profile)
    return {"ok": True, "path": str(p.path), "profile": p.data}


def resolve_period(period: str) -> dict:
    d0, d1 = resolve(period)
    return {"from": d0.isoformat(), "to": d1.isoformat(), **classify(d0, d1)}


def prepare(period: str, only: list[str] | None = None, without: list[str] | None = None,
            profile: str | None = None) -> dict:
    p, r = _ctx(profile)
    d0, d1 = resolve(period)
    c = _prepare(p, r, d0, d1, only=only, without=without)
    rd = run_dir(p, c["run_id"])
    return {"ok": True, "run_id": c["run_id"], "run_dir": str(rd), "proposal_path": str(rd / "proposal.json"), **c}


def validate(run_id: str, proposal: dict | None = None, proposal_path: str | None = None,
             profile: str | None = None) -> dict:
    """If `proposal` is given it is saved as the run's proposal.json first (MCP hosts have no file tool)."""
    p, r = _ctx(profile)
    rd, ev = _run(p, run_id)
    if proposal is not None:
        if not isinstance(proposal, dict) or "changes" not in proposal:
            raise ApiError('proposal must be an object like {"run_id": ..., "changes": [...]}')
        f = check_writable(p, rd / "proposal.json")
        f.write_text(json.dumps(proposal, indent=1, ensure_ascii=False), encoding="utf-8")
        prop = proposal
    else:
        prop = _proposal(rd, proposal_path)
    res = Validator(p, r, ev, Ledger(p.data_dir).rows()).run(prop)
    (rd / "validation.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    res["review_table"] = review_table(prop, res)
    return res


def commit(run_id: str, approval: str, proposal_path: str | None = None, profile: str | None = None) -> dict:
    p, r = _ctx(profile)
    rd, ev = _run(p, run_id)
    prop = _proposal(rd, proposal_path)
    led = Ledger(p.data_dir)
    res = Validator(p, r, ev, led.rows()).run(prop)
    if not res["ok"]:
        raise ApiError("proposal no longer validates", **res)
    if approval != approval_code(prop):
        raise ApiError("approval code does not match the reviewed proposal; "
                       "re-run validate and show the user the review table again")
    written = led.apply(prop["changes"], run_id=run_id, owner=p.owner, timezone=p.timezone,
                        rule_pack_version=r.version)
    (rd / "commit.json").write_text(json.dumps({"approval": approval, "entries": [w["entry_id"] for w in written]}))
    st = p.data_dir / "state.json"
    if st.exists():
        s = json.loads(st.read_text())
        for x in s.get("runs", []):
            if x["run_id"] == run_id:
                x["committed"] = True
        st.write_text(json.dumps(s, indent=1))
    return {"ok": True, "written": [{"entry_id": w["entry_id"], "voided": w["voided"], "account": w["account_name"],
                                     "type": w["activity_type"]} for w in written],
            "catalog": _refresh_catalog(p, r)}


def render(period: str, mirror: bool = True, profile: str | None = None) -> dict:
    p, r = _ctx(profile)
    d0, d1 = resolve(period)
    return {"ok": True, **_render(p, r, d0, d1, mirror=mirror), "catalog": _refresh_catalog(p, r)}


def read_output(period: str, profile: str | None = None) -> dict:
    """The latest Markdown deliverable of a period (for the AI to read back)."""
    p, r = _ctx(profile)
    d0, d1 = resolve(period)
    c = classify(d0, d1)
    f = p.data_dir / "output" / c["relpath"] / f"Salesforce_Activity_Log_{d0}_to_{d1}.md"
    if not f.exists():
        raise ApiError(f"no rendered log for {d0} to {d1} yet; run render first", folder=str(f.parent))
    return {"ok": True, "path": str(f), "markdown": f.read_text(encoding="utf-8")}


def ledger(period: str | None = None, include_voided: bool = False, profile: str | None = None) -> dict:
    p, r = _ctx(profile)
    rows = Ledger(p.data_dir).rows()
    if period:
        d0, d1 = resolve(period)
        rows = period_rows(rows, d0, d1, r)
    elif not include_voided:
        rows = [x for x in rows if not x["voided"]]
    return {"ok": True, "count": len(rows), "rows": rows}


# ---------------------------------------------------------------- activity notes (/log-activity-note)
def _day(day: str):
    d0, d1 = resolve(day or "today")
    if d0 != d1:
        raise ApiError(f"'{day}' is a range; a note is for one day (e.g. today, yesterday, 2026-10-14)")
    return d0


def note_context(day: str = "today", profile: str | None = None) -> dict:
    from . import notes_writer
    p, r = _ctx(profile)
    return notes_writer.context(p, r, _day(day))


def note_detail(ids: list[str], day: str = "today", profile: str | None = None) -> dict:
    from . import notes_writer
    p, r = _ctx(profile)
    return notes_writer.detail(p, r, _day(day), list(ids))


def note_targets(account: str, profile: str | None = None) -> dict:
    from . import notes_writer
    p, r = _ctx(profile)
    return notes_writer.targets(p, r, account)


def note_save(note: dict, target: str = "central", profile: str | None = None) -> dict:
    from . import notes_writer
    p, r = _ctx(profile)
    try:
        saved = notes_writer.save(p, r, note, target)
    except notes_writer.NoteError as e:
        raise ApiError(str(e)) from None
    return {**saved, "catalog": _refresh_catalog(p, r)}


def _refresh_catalog(p, r) -> str | None:
    from . import catalog
    return catalog.try_build(p, r)


def build_catalog(profile: str | None = None) -> dict:
    """Rebuild the catalog page: every note, record and rendered period, searchable."""
    from . import catalog
    p, r = _ctx(profile)
    return {"ok": True, **catalog.build(p, r)}


def docs_sync(account: str | None = None, dry_run: bool = False, rebuild: bool = False,
              profile: str | None = None) -> dict:
    """Convert changed documents of the selected accounts into the docs mirror (text copies)."""
    from . import docs_mirror
    p, r = _ctx(profile)
    try:
        return docs_mirror.sync(p, r, account=account, dry_run=dry_run, rebuild=rebuild)
    except docs_mirror.MirrorError as e:
        raise ApiError(str(e))


def docs_status(profile: str | None = None) -> dict:
    """Last docs mirror run: copies per account, size, the last report."""
    from . import docs_mirror
    p, _ = _ctx(profile)
    try:
        return docs_mirror.status(p)
    except docs_mirror.MirrorError as e:
        raise ApiError(str(e))


def account_add(name: str, *, kind: str = "customer", country: str | None = None, aliases=None,
                domains=None, folder: str | None = None, extra_folders=None, make_folder: bool = True,
                confirm: bool = False, profile: str | None = None) -> dict:
    """Plan (confirm=False) or add (confirm=True) a customer or partner, with its folder."""
    from . import add_customer
    return add_customer.add(name, profile=profile, kind=kind, country=country, aliases=aliases,
                            domains=domains, folder=folder, extra_folders=extra_folders,
                            make_folder=make_folder, confirm=confirm)
