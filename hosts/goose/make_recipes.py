"""Generate Goose recipes from the shared skill/SKILL.md (single source of truth).

Usage: python make_recipes.py <out_dir> <path-to-sfal-mcp>
"""
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]


def skill_body(name: str = "SKILL.md") -> str:
    text = (REPO / "skill" / name).read_text(encoding="utf-8")
    return text.split("---", 2)[2].strip() if text.startswith("---") else text


def extension(cmd: str) -> dict:
    return {"type": "stdio", "name": "sfal", "display_name": "SF Activity Log",
            "description": "SF Activity Log engine (calendar, email, notes, files -> Salesforce activity log)",
            "cmd": cmd, "args": [], "timeout": 900}


def recipes(cmd: str) -> dict[str, dict]:
    body = skill_body()
    goose_note = ("You are running in Goose. Use the sfal_* tools (MCP) for every engine operation; "
                  "there is no shell. Talk to the user in plain language and keep the review gate: "
                  "never call sfal_commit before the user approves the current review table.\n\n")
    return {
        "sf-log": {
            "version": "1.0.0",
            "title": "SF Activity Log",
            "description": "Build the Salesforce-ready presales engineer activity log for a period (today, last week, October, ...)",
            "instructions": goose_note + body,
            "prompt": "Build my Salesforce activity log for: {{ period }}",
            "parameters": [{"key": "period", "input_type": "string", "requirement": "required",
                            "description": "today, yesterday, this week, last week, this month, last month, "
                                           "<month>, YYYY-MM-DD or YYYY-MM-DD to YYYY-MM-DD"}],
            "extensions": [extension(cmd)],
        },
        "log-activity-note": {
            "version": "1.0.0",
            "title": "Log Activity Note",
            "description": "Capture what you just did (meeting, work, files) as an activity note while it is fresh",
            "instructions": goose_note.replace("never call sfal_commit before the user approves the current review table",
                                               "save a note only after the user confirms it") + skill_body("NOTE.md"),
            "prompt": "Log an activity note. {{ what }}",
            "parameters": [{"key": "what", "input_type": "string", "requirement": "optional", "default": "",
                            "description": "What you did, in your words (optional - leave empty to pick from today's meetings)"}],
            "extensions": [extension(cmd)],
        },
        "sf-add-customer": {
            "version": "1.0.0",
            "title": "SF Activity Log - Add Customer",
            "description": "Add a customer or partner to your profile and create its folder (asks for what is missing)",
            "instructions": goose_note + body,
            "prompt": "Add a customer to my SF Activity Log: {{ name }}. Follow the Add a customer section: "
                      "ask only for what is missing, show the plan, and apply it only after I say yes.",
            "parameters": [{"key": "name", "input_type": "string", "requirement": "optional", "default": "",
                            "description": "Customer or partner name as in Salesforce (optional - I will ask if empty)"}],
            "extensions": [extension(cmd)],
        },
        "sf-docs-sync": {
            "version": "1.0.0",
            "title": "SF Activity Log - Sync Documents",
            "description": "Make customer documents searchable (Word, PowerPoint, PDF). Type an account, 'dry run' or 'rebuild'",
            "instructions": goose_note.replace("keep the review gate: never call sfal_commit before the user "
                                               "approves the current review table", "report numbers exactly as returned")
                            + skill_body("DOCS.md"),
            "prompt": "Sync my customer documents into the docs mirror. {{ what }} "
                      "Follow the /sf-docs-sync section.",
            "parameters": [{"key": "what", "input_type": "string", "requirement": "optional", "default": "",
                            "description": "An account name, or 'dry run' to preview (optional)"}],
            "extensions": [extension(cmd)],
        },
        "sf-docs-status": {
            "version": "1.0.0",
            "title": "SF Activity Log - Docs Status",
            "description": "Docs mirror status: last run, copies per account, skipped files",
            "instructions": goose_note.replace("keep the review gate: never call sfal_commit before the user "
                                               "approves the current review table", "report numbers exactly as returned")
                            + skill_body("DOCS.md"),
            "prompt": "Show my docs mirror status. Follow the /sf-docs-status section.",
            "extensions": [extension(cmd)],
        },
        "sf-log-setup": {
            "version": "1.0.0",
            "title": "SF Activity Log - Setup",
            "description": "Set up (or update) your SF Activity Log profile: owner, folders, sources, accounts",
            "instructions": goose_note + body,
            "prompt": "Set me up for the SF Activity Log. Follow the Setup section: scan first, then interview me "
                      "one topic at a time, show the full profile, and save it only after I confirm.",
            "extensions": [extension(cmd)],
        },
    }


if __name__ == "__main__":
    out, cmd = Path(sys.argv[1]).expanduser(), sys.argv[2]
    out.mkdir(parents=True, exist_ok=True)
    for name, r in recipes(cmd).items():
        (out / f"{name}.yaml").write_text(yaml.safe_dump(r, sort_keys=False, allow_unicode=True, width=120),
                                          encoding="utf-8")
        print(out / f"{name}.yaml")
