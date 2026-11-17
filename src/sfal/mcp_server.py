"""MCP server - exposes the engine as tools for any MCP host (Goose, Claude Code, Open Worker, omp, Hermes, ...).

Run: sfal-mcp   (stdio transport)

Every tool returns a dict. Errors come back as {"ok": false, "error": "..."} rather than
raising, so weaker models can read and correct them. The workflow instructions served to
the host are the shared skill/SKILL.md (one source of truth for every host).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.resolve import Elicit, Resolve
from mcp.server.mcpserver import ElicitationResult
from pydantic import Field, create_model

from . import __version__, api, setup
from .ledger import LedgerError
from .period import PeriodError
from .profile import ProfileError
from .safety import BoundaryError


def _instructions() -> str:
    for p in (Path(__file__).resolve().parent / "SKILL.md",
              Path(__file__).resolve().parents[2] / "skill" / "SKILL.md"):
        if p.exists():
            text = p.read_text(encoding="utf-8")
            return text.split("---", 2)[2].strip() if text.startswith("---") else text
    return "SF Activity Log engine. Call sfal_doctor first."


server = MCPServer(name="sfal", title="SF Activity Log", version=__version__, instructions=_instructions())


def _safe(fn, *a, **kw) -> dict[str, Any]:
    try:
        return fn(*a, **kw)
    except api.ApiError as e:
        return {"ok": False, "error": str(e), **e.extra}
    except (ProfileError, PeriodError, LedgerError, BoundaryError, ValueError) as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:  # never crash the host session
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


@server.tool()
def sfal_doctor() -> dict[str, Any]:
    """Check the profile and access to every enabled source (calendar, mail, folders). Run first if anything fails."""
    return _safe(api.doctor)


@server.tool()
def sfal_rules() -> dict[str, Any]:
    """The org rule pack: 22 activity types with definitions, statuses, solution areas, account routing."""
    return _safe(api.rules)


@server.tool()
def sfal_profile_show() -> dict[str, Any]:
    """The user's profile (owner, sources, account registry). Read-only."""
    return _safe(api.profile_show)


@server.tool()
def sfal_resolve_period(period: str) -> dict[str, Any]:
    """Turn a period ('last week', 'October', '2026-10-01 to 2026-10-03', 'today') into dates and its output folder type."""
    return _safe(api.resolve_period, period)


@server.tool()
def sfal_prepare(period: str, only: list[str] | None = None, without: list[str] | None = None) -> dict[str, Any]:
    """Collect and pre-classify evidence for a period from the enabled sources.
    `only`/`without`: optional source names (calendar, email, files, notes, imports) for this run only.
    Returns run_id, source_reports, warnings, new_evidence, file_work, possible_unlogged_work, open_records."""
    return _safe(api.prepare, period, only=only, without=without)


@server.tool()
def sfal_validate(run_id: str, proposal: dict[str, Any]) -> dict[str, Any]:
    """Save and validate a proposal {"run_id": ..., "changes": [...]} against the logging guide rules.
    Returns ok, errors, warnings, held, review_table and (when ok) approval_code. Fix errors and call again."""
    return _safe(api.validate, run_id, proposal=proposal)


@server.tool()
def sfal_commit(run_id: str, approval_code: str) -> dict[str, Any]:
    """Write the validated proposal to the ledger. ONLY after the user explicitly approved the latest review table.
    approval_code must come from the latest successful sfal_validate."""
    return _safe(api.commit, run_id, approval_code)


@server.tool()
def sfal_render(period: str, copy_to_mirror: bool = True) -> dict[str, Any]:
    """Build the period's Excel (for the user) and Markdown (for you) from the ledger, in the period's output folder."""
    return _safe(api.render, period, mirror=copy_to_mirror)


@server.tool()
def sfal_catalog() -> dict[str, Any]:
    """Rebuild the catalog page (every activity note, ledger record and rendered period, searchable) and return its path.
    It also rebuilds itself after every note save, commit and render."""
    return _safe(api.build_catalog)


@server.tool()
def sfal_read_output(period: str) -> dict[str, Any]:
    """Read the latest rendered Markdown log of a period (to answer questions about it)."""
    return _safe(api.read_output, period)


@server.tool()
def sfal_ledger(period: str | None = None, include_voided: bool = False) -> dict[str, Any]:
    """Ledger rows: for a period, or all active rows (include_voided for full history)."""
    return _safe(api.ledger, period, include_voided=include_voided)


@server.tool()
def sfal_setup_scan(root: str | None = None, days: int = 60) -> dict[str, Any]:
    """Setup step 1: scan the customer folder, calendar and sent mail to PROPOSE a profile
    (owner, company domains, folder structure, account candidates, customer/partner domains, personal blocks).
    Writes nothing."""
    return _safe(setup.scan, root=root, days=days)


@server.tool()
def sfal_setup_save_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Setup step 2: validate and save the profile the user confirmed (previous profile kept as a backup)."""
    return _safe(setup.save_profile, profile)


@server.tool()
def sfal_account_add(name: str, kind: str = "customer", country: str | None = None,
                     aliases: list[str] | None = None, domains: list[str] | None = None,
                     folder: str | None = None, extra_folders: list[str] | None = None,
                     make_folder: bool = True, confirm: bool = False) -> dict[str, Any]:
    """Add a customer or partner to the profile and create its folder (default <country>/<name>/_ActivityLogging).
    Call with confirm=false first: it returns the plan, or `need: country` with `choices` to ask the user.
    Show the plan, and call again with confirm=true only after the user says yes. Never changes existing folders."""
    return _safe(api.account_add, name, kind=kind, country=country, aliases=aliases, domains=domains,
                 folder=folder, extra_folders=extra_folders, make_folder=make_folder, confirm=confirm)


@server.tool()
def sfal_docs_sync(account: str | None = None, dry_run: bool = False, rebuild: bool = False) -> dict[str, Any]:
    """Docs mirror: convert changed Word, PowerPoint, PDF (and name-matched Excel) files of the accounts
    selected in the profile into text copies for search. Read-only on the user's folders; writes only to
    the mirror folder. account: one account only. dry_run: show what would happen, write nothing.
    Report the counts, skipped reasons and `warning` as returned; offer the `next` step."""
    return _safe(api.docs_sync, account, dry_run, rebuild)


@server.tool()
def sfal_docs_status() -> dict[str, Any]:
    """Docs mirror: last run, copies per account, mirror size and the last report."""
    return _safe(api.docs_status)


@server.tool()
def sfal_note_context(day: str = "today") -> dict[str, Any]:
    """Activity note step 1: a day's meetings, sent mail and touched files (with account hints),
    the account list, the save mode, and notes already written that day."""
    return _safe(api.note_context, day)


@server.tool()
def sfal_note_detail(ids: list[str], day: str = "today") -> dict[str, Any]:
    """Activity note step 2: full detail for the items the note is about - invite description and attendee
    RSVPs (calendar), full message bodies of the thread (email), file titles/authors (files)."""
    return _safe(api.note_detail, ids, day)


@server.tool()
def sfal_note_targets(account: str) -> dict[str, Any]:
    """Activity note step 3: where a note for this account may be saved (central, or folders matched
    to the account). Use `recommended`; if it is null, ask the user to pick from `options`."""
    return _safe(api.note_targets, account)


@server.tool()
def sfal_note_save(note: dict[str, Any], target: str = "central") -> dict[str, Any]:
    """Activity note step 4, after the user confirmed: write the note (format in NOTE.md).
    note: {"title", "account", "activity_date", "summary", "topic"?, "activities": [{"title", "what", "time"?,
           "duration_hours"?, "hours_source"?, "context"?, "discussed"?, "outcomes"?, "next_steps"?,
           "people"?: [{"name", "role"|"status"}], "evidence"?: [ids]}], "follow_ups"?, "background"?:
           [{"text", "source"?}], "to_confirm"?}
    target: "central" or a `target` from sfal_note_targets options. Errors (e.g. hours vs meeting) come back
    as ok:false - fix and call again."""
    return _safe(api.note_save, note, target)


def _label(i: int, q: dict[str, Any]) -> str:
    """Prompt name the user sees, e.g. '1 · Tue 06 Oct 21:00 · Proseware Requirements Sync'."""
    title = q.get("title") or q.get("question") or ""
    parts = [str(i), q.get("when", "").strip(), title[:45].strip()]
    return " · ".join(p for p in parts if p)


def _decision_form(questions: list[dict[str, Any]]):
    """One elicitation form for all decisions: a choice per item (named after the item) + a details box.
    Defaults are pre-selected; answers are matched case-insensitively or by first letter."""
    from pydantic import ConfigDict
    fields: dict[str, Any] = {}
    for i, q in enumerate(questions, 1):
        options = [str(o) for o in (q.get("options") or ["Skip", "Log"])]
        default = q.get("default") if q.get("default") in options else options[0]
        fields[f"q{i}"] = (str, Field(default=default, alias=_label(i, q),
                                      description=q.get("reason", ""),
                                      json_schema_extra={"enum": options}))
    fields["details"] = (str, Field(default="", alias="Details (optional)",
                                    description="Hours or notes, e.g. '5: 1h, 6: 30m, I presented'"))
    return create_model("Decisions", __config__=ConfigDict(populate_by_name=True), **fields)


def _match(answer: str, options: list[str], default: str, known_hours: float | None = None) -> dict[str, Any]:
    """Interpret one typed answer. Returns {"answer": option|None, "hours": float|None, "unclear": reason|None}.
    Accepts the option (any case), its first letter, Enter (= default), or a duration: '1', '1.5h', '45m'
    (a bare number is hours) meaning 'log it with these hours'."""
    from .textdates import duration_hours
    a = (answer or "").strip().lower()
    if not a:
        return {"answer": default, "hours": None, "unclear": None}
    for o in options:
        if a == o.lower():
            return {"answer": o, "hours": None, "unclear": None}
    starts = [o for o in options if o.lower().startswith(a) or a.startswith(o.lower())]
    if len(starts) == 1:
        return {"answer": starts[0], "hours": None, "unclear": None}
    h = duration_hours(a)
    if h is not None and "Hours" in options:
        bare = a.replace(".", "", 1).isdigit()
        if h <= 0 or h > 12 or (bare and known_hours and h > 3 * known_hours):
            return {"answer": "Hours", "hours": h,
                    "unclear": f"'{answer}' read as {h:g}h - did you mean {h:g} minutes?" if bare else f"{h:g}h looks too long"}
        return {"answer": "Hours", "hours": h, "unclear": None}
    return {"answer": None, "hours": None, "unclear": f"'{answer}' is not one of {options}"}


def _load_decisions(run_id: str) -> list[dict[str, Any]]:
    import json as _json
    from .prepare import run_dir
    from .profile import load_profile
    f = run_dir(load_profile(), run_id) / "candidates.json"
    if not f.exists():
        raise api.ApiError(f"run {run_id} not found; call sfal_prepare first")
    return _json.loads(f.read_text()).get("decisions") or []


def _ask_resolver(run_id: str, only: list[int] | None = None) -> Elicit:
    qs = [q for q in _load_decisions(run_id) if not only or q["n"] in only]
    return Elicit(f"{len(qs)} item(s) need your call. Enter = keep [default]. Type s(kip), l(og), "
                  "or the time to log it with, e.g. 1.5h or 45m.",
                  _decision_form(qs))


@server.tool()
async def sfal_ask(run_id: str, result: Annotated[ElicitationResult[Any], Resolve(_ask_resolver)],
                   only: list[int] | None = None) -> dict[str, Any]:
    """Ask the user this run's `decisions` (from sfal_prepare) as ONE interactive form - pass just the run_id.
    `only`: optional decision numbers to ask (default: all). Returns one answer per decision plus the
    free-text details. If the host cannot show forms, returns ok:false - then use `decisions_text` in chat."""
    if getattr(result, "action", None) != "accept":
        return {"ok": True, "stopped": getattr(result, "action", "unknown"), "answers": [],
                "note": "user did not submit; ask in chat with decisions_text"}
    try:
        qs = [q for q in _load_decisions(run_id) if not only or q["n"] in only]
    except Exception as e:
        return {"ok": False, "error": str(e)}
    data = result.data.model_dump() if hasattr(result.data, "model_dump") else dict(result.data or {})
    answers, unclear = [], []
    for i, q in enumerate(qs, 1):
        raw = data.get(f"q{i}", "")
        m = _match(raw, q["options"], q["default"], q.get("hours"))
        if m["unclear"]:
            unclear.append({"n": q["n"], "title": q["title"], "typed": raw, "why": m["unclear"]})
        answers.append({"n": q["n"], "id": q["id"], "title": q["title"], "answer": m["answer"] or raw,
                        **({"hours": m["hours"]} if m["hours"] is not None else {})})
    out = {"ok": True, "answers": answers, "details": data.get("details", "")}
    if unclear:
        out["unclear"] = unclear
        out["note"] = "some answers did not match an option; confirm those in chat"
    return out


def main():
    server.run("stdio")


if __name__ == "__main__":
    main()
