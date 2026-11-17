# Commands reference

Day to day you only use the AI tool. These are the underlying commands, for checks and scripting.

## In your AI tool

| Goose Desktop | Goose terminal | OpenCode | Does |
|---|---|---|---|
| Recipes → **Log Activity Note** → ▶ | `goose run --recipe log-activity-note -s` | `/log-activity-note <what you did>` | capture an activity note |
| Recipes → **SF Activity Log** → ▶ | `goose run --recipe sf-log --params period="last week" -s` | `/sf-log last week` | log a period |
| Recipes → **SF Activity Log - Setup** → ▶ | `goose run --recipe sf-log-setup -s` | `/sf-log-setup` | create / update your profile |
| Recipes → **SF Activity Log - Add Customer** → ▶ | `goose run --recipe sf-add-customer -s` | `/sf-add-customer` | add a customer or partner, with its folder |
| Recipes → **SF Activity Log - Sync Documents** → ▶ | `goose run --recipe sf-docs-sync -s` | `/sf-docs-sync [account] [dry run]` | make customer documents searchable (docs mirror) |
| Recipes → **SF Activity Log - Docs Status** → ▶ | `goose run --recipe sf-docs-status -s` | `/sf-docs-status` | last docs mirror run |

Claude Code: the same commands as OpenCode ([Get started with Claude Code](../start/claude-code.md)).
Hermes: the same commands as OpenCode, as skills ([Get started with Hermes](../start/hermes.md)).
omp: the same commands as OpenCode ([Get started with omp](../start/omp.md)).
Open Worker: ask in words - *log activity note: …*, *sf-log last week*, *sf-log-setup*, *sf-docs-sync* ([Get started with Open Worker](../start/openworker.md)).

Open a recipe in the Desktop app from the terminal: `goose recipe open sf-log --param period="last week"`.

## Periods

`today` · `yesterday` · `this week` · `last week` · `this month` · `last month` ·
`last N days` · `<month> [year]` · `YYYY-MM-DD` · `YYYY-MM-DD to YYYY-MM-DD`

Weeks run Monday–Sunday. A month name means its most recent occurrence.

## Engine CLI

`~/.sf-activity-log/bin/sfal <command>` - every command prints JSON.

| Command | Does |
|---|---|
| `doctor` | check profile and access to every enabled source |
| `profile init --owner "Last, First" --data-dir <dir> [--domain d]` | write a starter profile |
| `profile show` | print the profile |
| `rules` | print the rule pack |
| `setup-scan [--root <dir>] [--days 60]` | propose a profile from your folders, calendar and mail |
| `account-add "<name>" [--kind customer\|partner] [--country C] [--alias A]… [--domain D]… [--folder P] [--extra-folder F]… [--no-folder] [--yes]` | add a customer or partner and its folder; without `--yes` it only shows the plan |
| `prepare <period> [--only a,b] [--without c]` | collect and pre-classify evidence |
| `validate <run_id> [--proposal file]` | check a proposal against the rules |
| `commit <run_id> --approval <code>` | write an approved proposal to the ledger |
| `render <period> [--no-mirror]` | build the period's Excel + Markdown |
| `ledger [<period>] [--all]` | show records (`--all` includes voided) |
| `note-context [day]` | a day's meetings, mail and files for an activity note |
| `note-detail <id>… [--day d]` | full detail for chosen items: invite text, attendee RSVPs, email bodies, files |
| `note-targets <account>` | where a note for an account may be saved |
| `note-save --file note.json [--target t]` | write an activity note (`central` or a target from `note-targets`) |
| `catalog [--open]` | rebuild the catalog page (every note, record and period); `--open` opens it |
| `docs sync [--account A] [--dry-run] [--rebuild]` | docs mirror: convert changed documents of the selected accounts into text copies |
| `docs status` | docs mirror: last run, copies per account, size |

Global option: `--profile <path>` (or `$SFAL_PROFILE`) to use another profile.

## MCP tools (used by Goose)

| Tool | Does |
|---|---|
| `sfal_doctor` | health check |
| `sfal_rules` | rule pack |
| `sfal_profile_show` | profile |
| `sfal_resolve_period` | period → dates and output folder |
| `sfal_prepare` | collect evidence |
| `sfal_ask` | ask this run's questions as an interactive form |
| `sfal_validate` | check a proposal; returns review table and approval code |
| `sfal_commit` | write to the ledger (needs the approval code) |
| `sfal_render` | build Excel + Markdown |
| `sfal_read_output` | read a period's Markdown log |
| `sfal_ledger` | records |
| `sfal_setup_scan` | propose a profile |
| `sfal_setup_save_profile` | save a confirmed profile |
| `sfal_account_add` | add a customer or partner: plan first (`confirm` false), then apply (`confirm` true) |
| `sfal_note_context` | a day's meetings, mail and files for an activity note |
| `sfal_note_detail` | full detail for chosen items (invite, attendees, email bodies, files) |
| `sfal_note_targets` | where a note for an account may be saved |
| `sfal_note_save` | write an activity note |
| `sfal_catalog` | rebuild the catalog page and return its path |
| `sfal_docs_sync` | docs mirror: convert changed documents (`account`, `dry_run`, `rebuild`) |
| `sfal_docs_status` | docs mirror: last run, copies per account, size |
