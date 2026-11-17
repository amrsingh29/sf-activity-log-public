"""sfal - command line interface. The one interface every AI host (OpenCode, Claude Code, ...) drives.

All commands print JSON to stdout (exit 0 = ok, 1 = validation/user error, 2 = environment error).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


from . import __version__, api
from .ledger import LedgerError
from .period import PeriodError
from .profile import ProfileError, profile_path
from .safety import BoundaryError


def out(obj, code: int = 0):
    print(json.dumps(obj, indent=1, ensure_ascii=False, default=str))
    sys.exit(code)


def _csv(v):
    return [s.strip() for s in v.split(",") if s.strip()] if v else None


def _period(args) -> str:
    return " ".join(args.period)


# ---------------------------------------------------------------- commands (thin: logic lives in api.py)
def cmd_doctor(args):
    r = api.doctor(args.profile)
    out(r, 0 if r["ok"] else 2)


def cmd_profile_init(args):
    dest = profile_path(args.profile)
    if dest.exists() and not args.force:
        out({"ok": False, "error": f"profile already exists at {dest}; use --force to overwrite"}, 1)
    template = Path(__file__).resolve().parent / "profile_template.yaml"
    text = template.read_text()
    text = text.replace("__OWNER__", args.owner).replace("__DATA_DIR__", args.data_dir) \
        .replace("__DOMAIN__", args.domain or "example.com").replace("__TZ__", args.timezone)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    out({"ok": True, "profile": str(dest), "next": "edit accounts/sources, then run: sfal doctor"})


def cmd_profile_show(args):
    out(api.profile_show(args.profile))


def cmd_rules(args):
    out(api.rules(args.profile))


def cmd_prepare(args):
    out(api.prepare(_period(args), only=_csv(args.only), without=_csv(args.without), profile=args.profile))


def cmd_validate(args):
    r = api.validate(args.run_id, proposal_path=args.proposal, profile=args.profile)
    out(r, 0 if r["ok"] else 1)


def cmd_commit(args):
    out(api.commit(args.run_id, args.approval, proposal_path=args.proposal, profile=args.profile))


def cmd_render(args):
    out(api.render(_period(args), mirror=not args.no_mirror, profile=args.profile))


def cmd_ledger(args):
    out(api.ledger(_period(args) if args.period else None, include_voided=args.all, profile=args.profile))


def cmd_note_context(args):
    out(api.note_context(" ".join(args.day) or "today", profile=args.profile))


def cmd_note_detail(args):
    out(api.note_detail(args.ids, day=args.day, profile=args.profile))


def cmd_note_targets(args):
    out(api.note_targets(" ".join(args.account), profile=args.profile))


def cmd_note_save(args):
    note = json.loads(Path(args.file).read_text())
    out(api.note_save(note, target=args.target, profile=args.profile))


def cmd_setup_scan(args):
    from . import setup
    out(setup.scan(root=args.root, days=args.days, profile=args.profile))


def cmd_catalog(args):
    res = api.build_catalog(profile=args.profile)
    if args.open:
        import subprocess
        subprocess.run(["open", res["path"]], check=False)
    out(res)


def cmd_account_add(args):
    res = api.account_add(" ".join(args.name), kind=args.kind, country=args.country, aliases=args.alias,
                          domains=args.domain, folder=args.folder, extra_folders=args.extra_folder,
                          make_folder=not args.no_folder, confirm=args.yes, profile=args.profile)
    out(res, 0 if res.get("ok") else 1)


def cmd_docs_sync(args):
    out(api.docs_sync(account=" ".join(args.account) if args.account else None, dry_run=args.dry_run,
                      rebuild=args.rebuild, profile=args.profile))


def cmd_docs_status(args):
    out(api.docs_status(profile=args.profile))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="sfal", description="SF Activity Log engine")
    ap.add_argument("--profile", help="profile path (default ~/.sf-activity-log/profile.yaml or $SFAL_PROFILE)")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="check profile, data folder and source access").set_defaults(fn=cmd_doctor)

    pr = sub.add_parser("profile", help="create or show the personal profile")
    psub = pr.add_subparsers(dest="pcmd", required=True)
    pi = psub.add_parser("init")
    pi.add_argument("--owner", required=True, help='Salesforce Primary Owner, e.g. "Lee, Sam"')
    pi.add_argument("--data-dir", required=True)
    pi.add_argument("--domain", help="your company email domain, e.g. mycompany.example")
    pi.add_argument("--timezone", default="Asia/Singapore")
    pi.add_argument("--force", action="store_true")
    pi.set_defaults(fn=cmd_profile_init)
    psub.add_parser("show").set_defaults(fn=cmd_profile_show)

    sub.add_parser("rules", help="print the org rule pack (types, routing)").set_defaults(fn=cmd_rules)

    pp = sub.add_parser("prepare", help="collect + pre-classify evidence for a period")
    pp.add_argument("period", nargs="+")
    pp.add_argument("--only", help="comma list of sources for this run")
    pp.add_argument("--without", help="comma list of sources to skip for this run")
    pp.set_defaults(fn=cmd_prepare)

    pv = sub.add_parser("validate", help="check a proposal against the rule pack")
    pv.add_argument("run_id")
    pv.add_argument("--proposal")
    pv.set_defaults(fn=cmd_validate)

    pc = sub.add_parser("commit", help="write an approved proposal to the ledger")
    pc.add_argument("run_id")
    pc.add_argument("--approval", required=True, help="approval code shown by validate, after the user approved")
    pc.add_argument("--proposal")
    pc.set_defaults(fn=cmd_commit)

    pr2 = sub.add_parser("render", help="build the period deliverable from the ledger")
    pr2.add_argument("period", nargs="+")
    pr2.add_argument("--no-mirror", action="store_true")
    pr2.set_defaults(fn=cmd_render)

    pl = sub.add_parser("ledger", help="show ledger rows")
    pl.add_argument("period", nargs="*")
    pl.add_argument("--all", action="store_true", help="include voided rows")
    pl.set_defaults(fn=cmd_ledger)

    nc = sub.add_parser("note-context", help="a day's meetings, mail and files for an activity note")
    nc.add_argument("day", nargs="*", help="default: today")
    nc.set_defaults(fn=cmd_note_context)
    nd = sub.add_parser("note-detail", help="full detail (invite, attendees, email bodies, files) for chosen items")
    nd.add_argument("ids", nargs="+")
    nd.add_argument("--day", default="today")
    nd.set_defaults(fn=cmd_note_detail)
    nt = sub.add_parser("note-targets", help="where a note for an account may be saved")
    nt.add_argument("account", nargs="+")
    nt.set_defaults(fn=cmd_note_targets)
    ns = sub.add_parser("note-save", help="write an activity note (JSON file) to central or a matched folder")
    ns.add_argument("--file", required=True)
    ns.add_argument("--target", default="central", help="central, or a folder path returned by note-targets")
    ns.set_defaults(fn=cmd_note_save)

    pg = sub.add_parser("catalog", help="rebuild the catalog page of every note, record and period")
    pg.add_argument("--open", action="store_true", help="open it in the browser")
    pg.set_defaults(fn=cmd_catalog)

    pa = sub.add_parser("account-add", help="add a customer or partner to the profile, with its folder")
    pa.add_argument("name", nargs="+", help="account name as in Salesforce")
    pa.add_argument("--kind", default="customer", choices=["customer", "partner"])
    pa.add_argument("--country", help="country folder (needed when customers sit one level down)")
    pa.add_argument("--alias", action="append", help="another spelling, repeatable")
    pa.add_argument("--domain", action="append", help="their email domain, repeatable")
    pa.add_argument("--folder", help="folder path inside the workspace, if not <country>/<name>")
    pa.add_argument("--extra-folder", action="append", help="extra folder to create, repeatable")
    pa.add_argument("--no-folder", action="store_true", help="add the profile entry only")
    pa.add_argument("--yes", action="store_true", help="apply; without it only the plan is shown")
    pa.set_defaults(fn=cmd_account_add)

    pdocs = sub.add_parser("docs", help="docs mirror: text copies of Word, PowerPoint, PDF and Excel files for search")
    dsub = pdocs.add_subparsers(dest="dcmd", required=True)
    dsy = dsub.add_parser("sync", help="convert changed documents of the selected accounts")
    dsy.add_argument("--account", nargs="+", help="only this account (name or alias)")
    dsy.add_argument("--dry-run", action="store_true", help="show what would happen, write nothing")
    dsy.add_argument("--rebuild", action="store_true", help="convert everything again; allows large removals")
    dsy.set_defaults(fn=cmd_docs_sync)
    dsub.add_parser("status", help="last run, copies per account, size").set_defaults(fn=cmd_docs_status)

    ps = sub.add_parser("setup-scan", help="scan folders, calendar and sent mail to propose a profile")
    ps.add_argument("--root", help="customer/project folder to scan (default: profile workspace.root)")
    ps.add_argument("--days", type=int, default=60)
    ps.set_defaults(fn=cmd_setup_scan)

    args = ap.parse_args(argv)
    try:
        args.fn(args)
    except api.ApiError as e:
        out({"ok": False, "error": str(e), **e.extra}, 1)
    except (ProfileError, PeriodError, LedgerError, BoundaryError) as e:
        out({"ok": False, "error": str(e)}, 1)


if __name__ == "__main__":
    main()
