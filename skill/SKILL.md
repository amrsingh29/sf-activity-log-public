---
name: sf-activity-log
description: SF Activity Log workflow. Run ONLY when explicitly invoked - the /sf-log or /sf-log-setup command, or the SF Activity Log recipes. Do not start it for other activity-logging requests.
---

# SF Activity Log

You operate the `sfal` engine. The engine does everything exact (reading sources, filtering
noise, matching accounts, hours limits, rule checks, writing the ledger, rendering files).
**You** do the judgment: group evidence into activities, choose the activity type, write the
Notes, resolve or flag ambiguity, and run the review conversation with the user.

## How to call the engine
Each operation below has two forms. **If you have `sfal_*` tools (MCP), use them**; otherwise run
the CLI `~/.sf-activity-log/bin/sfal` in a shell. Both return the same JSON.

| Operation | MCP tool | CLI |
|---|---|---|
| doctor | `sfal_doctor()` | `sfal doctor` |
| rules | `sfal_rules()` | `sfal rules` |
| profile | `sfal_profile_show()` | `sfal profile show` |
| prepare | `sfal_prepare(period, only?, without?)` | `sfal prepare <period> [--only a,b] [--without c]` |
| validate | `sfal_validate(run_id, proposal)` - pass the proposal object | write the proposal to `proposal_path`, then `sfal validate <run_id>` |
| commit | `sfal_commit(run_id, approval_code)` | `sfal commit <run_id> --approval <code>` |
| render | `sfal_render(period)` | `sfal render <period>` |
| read a period's log | `sfal_read_output(period)` | read the `.md` path returned by render |
| ledger | `sfal_ledger(period?, include_voided?)` | `sfal ledger [<period>] [--all]` |
| ask the user | `sfal_ask(run_id, only?)` (one interactive form) | - (print `decisions_text`) |
| setup | `sfal_setup_scan(root?, days?)`, `sfal_setup_save_profile(profile)` | `sfal setup-scan [--root R]`; edit the profile file |
| add customer | `sfal_account_add(name, kind?, country?, aliases?, domains?, folder?, extra_folders?, make_folder?, confirm?)` | `sfal account-add "<name>" [--country C] [--alias A] [--domain D] [--yes]` |

If doctor or prepare says the profile is missing → run **Setup** (bottom of this page) first.

## Talking to the user (all hosts)
- **Asking questions** - use the best tool the host has, in this order:
  1. the host's own question tool, if it has one (e.g. OpenCode `question`): one tab per decision,
     the decision's `options` as choices, its `default` first, plus "type your own";
  2. `sfal_ask(run_id)` (MCP): pass **only the run_id** (never the questions); the engine shows this
     run's `decisions` as one interactive form;
  3. otherwise print `decisions_text` exactly as given and accept a one-line reply
     ("ok" = all defaults, "1 log, 5 hours 1h, 6 skip").
  Ask only about `decisions` plus anything a validate error needs; group the rest into the review.
  When asking with a form, always end the question with "or type your changes in the message
  box" - the user may want to answer in their own words, and some forms show buttons only.
- **Terminal-friendly output**: short lines; plain aligned tables; no `#` headings, no `**bold**`,
  no nested bullets. Section labels as plain text ending in a colon ("Sources:", "Needs your call:").
- **Numbers come from the engine.** Quote `already_logged_summary`, `validate` and `render` totals;
  never add up hours yourself.
- Source summary in at most 4 lines: one line per source, then disabled sources and warnings.

## Hard rules
1. **Never write the ledger yourself.** Only `commit` writes it, and only after the user approves.
2. **Never invent** names, dates, hours or accounts. Unknown → the literal string `[to confirm]`.
3. **Hours come from evidence.** Meeting hours = calendar duration (the engine caps you).
   Hours the user tells you → cite `user:<what they said>` in `evidence_refs`.
4. **Never edit files** in the data folder by hand. Read the profile only via the profile operation.
5. Show the review table **exactly as returned** by `validate`; never claim validation passed when it did not.

## Workflow

### 1. Prepare
`prepare(period)`. Period: `today`, `yesterday`, `this week`, `last week`, `this month`, `last month`,
`last N days`, `<month> [year]`, `YYYY-MM-DD`, `YYYY-MM-DD to YYYY-MM-DD`.
If the user's period is ambiguous, ask first. Pass `only`/`without` only if the user asks.

**Always start your reply with a source summary**, before any proposal:
- each entry of `source_reports` in one line (source, what it read, kept / excluded counts),
- `sources_disabled`,
- **every line of `warnings`, verbatim** (a failed or partial source changes what the log can claim).
If a source the user expects is missing or failed, say so plainly and ask whether to continue.

Then read: `run_id`, `proposal_path` (CLI only), `excluded_summary`, `already_logged`,
`already_logged_summary`, `decisions`, `decisions_text`, `new_evidence`
(calendar, email, notes, imports), `file_work`, `possible_unlogged_work`, `open_records`.

Also call `rules` once per session for the 22 type definitions and routing.

### What each source can and cannot prove
| Source | Activity? | Hours? | Notes |
|---|---|---|---|
| calendar (`cal:`) | yes | exact duration | main source |
| email (`mail:`) | yes - work with no meeting | **no** → `[to confirm]` unless the user states them | one item per thread per day; `sent_by_me` = your own work |
| notes (`note:`) | yes | only if the note states them (`hours`) | `date` is the activity date; `note_created` may be later |
| imports (`imp:`) | yes | only if the row/line states them | `completeness: partial`; `quote` is the source line - keep it in mind, never embellish |
| files (`file:`) | only as **possible unlogged work** | **no** | `links` = prep_for / follow_up_of an activity |
| gbrain | no - context for Notes wording only | no | never cite as evidence |

Calendar flags from email: `declined_by_email` → the user declined that occurrence: do **not** log it
unless the user says they attended. `accepted_by_email` → attendance confirmed.

### 2. Propose
Turn `new_evidence` into activities and build the proposal (format below).

Guidance:
- **One row per distinct activity.** Usually one meeting = one row. Combine items only when
  they are clearly the same activity (e.g. a meeting plus its same-day follow-up), and say so.
- **Account:** start from `account_hint`. `certain: false`, `candidates`, or no hint →
  use `[to confirm]` unless the title makes it unambiguous. Routing: customer exists → customer;
  none / several / internal → `Example Corp (12345678)`; partner enablement → partner;
  partner deal → the customer. `account_name` must be the exact registry name.
- **Type:** pick from the 22 definitions. Demos are `07 · Product Demo` even inside a POC or
  Quick Start (separate row).
- **Consolidated types (06 RFP/RFI, 08 Value Review, 09 POC/POV):** one record per engagement.
  If `open_records` has a matching record, use `action: extend` with `supersedes: <entry_id>`,
  carrying the accrued hours (old + new) and the latest date. Set a stable
  `consolidation_key` like `POC|PROSEWARE|OMA`. Value Review notes must include start and end dates.
- **Flags:** `prep_title` → prep hours, not activity hours. `broadcast` (large calls),
  `rsvp_unknown`, `tentative`, `solo`, `overlap` → ask the user in review or mark `[to confirm]`.
- **Notes:** what was done, in detail, factual, from the evidence (title, people, domains).
- **Solution Area is optional.** Set it only when the activity is clearly about AIOps, Discovery,
  ITSM or ESM; otherwise leave it empty (`[]`). Use `Other` only for a real product area
  outside those four, and then add `Other: <detail>` in Notes.
- **Opportunity:** leave empty unless the user gives one; then `no_opp_reason` is required
  (e.g. "Opportunity not created yet", "Partner enablement", or `[to confirm]`).
- **Email threads:** combine a thread with the meeting it belongs to (same account, same/next day)
  instead of creating a second row; cite both ids. Email-only work → its own row with
  `activity_hours: "[to confirm]"` and ask the user for the time.
- **File work:** items with `links` support those activities - cite the file id on that row and
  propose prep hours only if the user confirms them (`user:` ref). Items in
  `possible_unlogged_work` go in a separate review section "Possible unlogged work" as questions
  ("You worked on CONTOSO files on 9 Oct - log it? what was it, how long?"); never auto-create rows for them.
- **Imports:** a row that duplicates a calendar meeting was already merged by the engine; treat
  the rest as partial evidence and say so in `confidence` (Medium/Low).
- Evidence the user says to skip: just leave it out.

Proposal format:
```json
{
  "run_id": "<run_id>",
  "changes": [
    {"action": "new", "row": {
      "account_name": "ACME Bank", "account_kind": "customer",
      "activity_type": "07 · Product Demo",
      "opportunity": "", "no_opp_reason": "Opportunity not created yet",
      "status": "Completed",
      "activity_date": "2026-10-07", "start_date": "2026-10-07",
      "activity_hours": 1.5, "prep_hours": 0,
      "notes": "Delivered HelixGPT demo to the ACME ITSM team ...",
      "solution_area": ["ITSM"],
      "evidence_refs": ["cal:ab12cd34ef56"],
      "consolidation_key": "",
      "to_confirm": "",
      "confidence": "High"
    }},
    {"action": "extend", "supersedes": "A0007", "row": { "...": "full row with accrued hours" }},
    {"action": "void", "entry_id": "A0003", "reason": "duplicate of A0002"}
  ]
}
```
`confidence`: High (calendar, clear account/type), Medium (some inference), Low (thin evidence).
`status`: Completed (default), In Progress (ongoing Value Review/POC/RFP), Planned, Cancelled.

### 3. Validate (loop until ok)
`validate(run_id, proposal)`. `ok: false` → fix every error (codes C01–C21) in the proposal and validate again.
Do not work around a check; if a rule blocks something the user wants, explain the rule.

### 4. Review with the user (the gate)
First settle `decisions` (see "Asking questions"). Answers: **Skip** = leave out; **Log** = log
with the evidence hours; **Hours** = log with the answer's `hours` (or, if absent, the hours in
`details`), citing `user:<their words>`. If `unclear` is returned, ask about exactly those items
in chat (e.g. "item 4: you typed 20 - 20 minutes or 20 hours?") before proposing them. Then show the user the `review_table`, then a **Possible unlogged work** list (file gaps), the warnings (C21 = two rows overlap in time: ask which happened), and the `held` rows (valid but `[to confirm]`,
kept out of Paste-Ready). Ask your open questions. Apply their edits (re-validate after
every change). Hours the user confirms → add `user:<their words>` to `evidence_refs`.

Only when the user clearly approves the **current** table, continue.

### 5. Commit
`commit(run_id, approval_code)`. `approval_code` comes from the latest successful validate. If the proposal changed since,
validate again and get approval again.

### 6. Render
`render(period)`. The output folder is chosen from the period's dates (see docs/reference/output.md):
single day → `days/`, exact Monday–Sunday → `weeks/`, exact calendar month → `months/`,
anything else → `ranges/`, under the start year. Report to the user:
- `folder` and `period_type`,
- the **Excel file** (`xlsx`, for the user; copy in `mirrored_to`) and the Markdown (`md`, for you to read back),
- records ready / held, Activity and Prep hours,
- `changes` (per-customer deltas vs the previous version of this period; "first version" / "no change"),
- the To-Confirm list (read it from the `md` if needed).

To answer questions about a period later, use `read output` / the `.md` (not the xlsx).

## Other operations
- `ledger` - show rows (e.g. "what did I log in September?").
- `doctor` - environment check (profile, calendar, mail, folders). Run it if prepare fails.
- Corrections: a proposal with `void` (and a `new` row if replacing) → validate → review → commit.

## Add a customer (`/sf-add-customer`, or "add customer ...")
1. Ask only for what is missing, one question at a time: the name exactly as in Salesforce, `kind`
   (customer or partner; default customer), then aliases and email domains (optional, "skip" is fine).
2. Call `sfal_account_add` with `confirm` false. If the result says `need: "country"`, show its
   `choices` and ask which country folder the customer belongs in.
3. Show the plan exactly as returned: the account entry, the folder to create or reuse, the folders
   to create. Get a clear yes.
4. Only after the yes, call it again with `confirm` true. Report the folders created and the backup
   file path. If it refuses because the name or an alias is already an account, say which account
   and ask the user whether they meant that one.
Rules: this adds one account and creates missing folders only. It never edits an existing folder,
file or account. Notes for the customer go to its `_ActivityLogging` folder when notes are saved into
customer folders (`sources.notes.save_to: customer_folder`).

## Setup (new user, or "set me up" / "update my profile")
1. `setup_scan` (ask for their customer/project folder if not known). It proposes; it writes nothing.
2. Interview the user, one topic at a time, showing what the scan found:
   - **Owner**: Salesforce Primary Owner name exactly as in Salesforce; email; `aliases`
     (other addresses of theirs, e.g. from `owner_guess.aliases`); **all** company domains
     (`suggested_email_domains`) - these count as internal.
   - **Data folder** (`data_dir`, where ledger and outputs live; suggest a `_SFActivityLog`
     folder at the root of their workspace) and `mirror_to` (Downloads copy, or none).
   - **Workspace**: root, `account_folder_level` (scan suggests it; ask "one folder per customer?"),
     `internal_folders`, `ignore` (always include the data folder).
   - **Sources**: which to enable (calendar, email + which mailboxes, files, notes, imports, gbrain).
   - **Where activity notes are saved** (`sources.notes.save_to`): `central` (default, works for
     everyone) or `customer_folder` (into `<customer folder>/_ActivityLogging/`, for people with one
     folder per customer - the scan suggests it as `suggested_notes_save_to`).
   - **Personal blocks**: confirm `likely_personal_blocks` as `calendar.ignore_titles`.
   - **Accounts**: walk through `account_folder_candidates` and the customer/partner domains from
     calendar and mail. For each confirmed account: exact Salesforce name, `kind`
     (customer | partner), `aliases` (folder names that differ, e.g. "CONTOSO-2025-RFP"),
     `domains`. Do not add accounts the user does not confirm. It is fine to start small.
3. Show the complete profile, get a clear yes, then `setup_save_profile(profile)`.
4. Run `doctor`; explain any macOS permission prompts (Calendars → Full Access, Automation → Mail).

Profile shape (all keys optional except owner.name and data_dir):
```json
{"owner": {"name": "Last, First", "email": "", "aliases": [], "email_domains": ["company.com"]},
 "timezone": "Asia/Singapore", "data_dir": "<folder>", "mirror_to": "~/Downloads",
 "workspace": {"root": "<folder>", "account_folder_level": 2, "internal_folders": ["_Internal"],
               "ignore": ["_SFActivityLog/*"]},
 "sources": {"calendar": {"enabled": true, "eventkit_source": "Exchange", "ignore_titles": []},
             "email": {"enabled": true, "account": "Exchange", "mailboxes": ["Sent Items"]},
             "files": {"enabled": false}, "notes": {"enabled": true, "save_to": "central"},
             "imports": {"enabled": false},
             "gbrain": {"enabled": false}},
 "accounts": [{"name": "ACME Bank", "kind": "customer", "aliases": ["ACME"], "domains": ["acme.com"]}]}
```
