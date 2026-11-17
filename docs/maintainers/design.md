---
title: SF Activity Log — Design
version: 1.0 (for sign-off)
date: 2026-10-14
owner: Alex Lee
status: Draft — awaiting sign-off, build not started
---

# SF Activity Log — Design

A repeatable, agent-operated tool that turns the evidence of a presales engineer's work — calendar, email, project files, notes — into an accurate, Salesforce-ready activity log for any period, following the **your company's logging guide v1.0 (Oct 2026)**.

It is a **fresh build**. The earlier `Project/_ActivityLogging/` pipeline is not reused, migrated or modified.

---

## 1. Goals, success criteria, non-goals

**Goals**
- Assemble evidence for a period automatically; propose one Salesforce-ready row per activity.
- Apply the logging guide rules (type, account routing, hours split, consolidation) consistently, enforced by code.
- Keep the user in control: review before anything is written; unknowns marked `[to confirm]`.
- Be adoptable by any presales engineer with minor, guided configuration — no code changes.

**Success criteria**
- Nothing billable forgotten; every logged hour traceable to evidence.
- Zero logging guide rule violations in proposed rows.
- A weekly log in minutes; any past period can be rebuilt (late evidence appears in that period).
- One append-only ledger; corrections visible; evidence trail preserved.

**Non-goals (v1)**
- No live Salesforce integration — output is paste-ready.
- No writes outside the configured data folder and the optional Downloads mirror. Customer folders, calendar and mailbox are read-only.
- No inferred facts (names, dates, hours) without evidence.
- Windows support (see §14).
- The daily per-customer journaling flow stays separate; its notes are an input only.

---

## 2. Decisions log

| # | Decision | Rationale |
|---|---|---|
| D1 | Fresh build; old `_ActivityLogging/` left untouched | Old pipeline has known flaws; no migration |
| D2 | Primary host **OpenCode + Cortex**; Claude Code wrapper secondary | Cortex is the company-approved in-house AI |
| D3 | Host-agnostic **engine** (Python CLI) + **MCP server** + shared `SKILL.md` + thin host wrappers | Same results in any agent tool; new hosts are cheap to add |
| D4 | Deterministic work in the engine; the model only groups evidence, proposes type/account and writes Notes | Results must not depend on model strength |
| D5 | Three layers: engine · org rule pack · personal profile | Colleagues change one profile file, nothing else |
| D6 | Calendar via **EventKit** (macOS Calendar with Exchange account); fallback = imported documents | Tested 14 Oct: complete, recurrences expanded, stable format |
| D7 | Email via **Mail.app automation**; fallback = imported documents | Tested 14 Oct: Sent Items readable; no Full Disk Access needed |
| D8 | Mac only for v1 | Pilot platform; no install restrictions |
| D9 | Weekly main run (guide: "Log weekly") | Matches company expectation |
| D10 | Data folder separate from code, configurable; default `Project/_SFActivityLog/` | Aggregate output belongs at root, not per customer |
| D11 | Timezone stored on every ledger row | Colleagues outside UTC+8 |
| D12 | Primary Owner filled from profile on every row | Required SF field |
| D13 | Demos inside a POC/POV log separately as 07 (configurable) | User's rule; consistent with guide's Quick Start note |
| D14 | Imported documents (Copilot / manual: docx, xlsx, csv, txt, md) are a source of their own, replacing per-source fallbacks | One simple path for anything without live access |
| D15 | Every source can be enabled/disabled in the profile and per run | User controls what evidence is used |
| D16 | Email reads only the mailboxes the user lists; no mail-folder→account mapping | Keep it simple |
| D17 | Account registry is the source of truth; folder structure is an optional hint | Works for people without folder discipline |

---

## 3. Architecture

```
                    ┌──────────────── Agent host ────────────────┐
                    │  OpenCode + Cortex  (primary)              │
                    │  Claude Code         (secondary)           │
                    │  SKILL.md workflow  +  /sf-log commands    │
                    └───────────────┬────────────────────────────┘
                                    │ MCP tools (or CLI)
┌───────────────────────────────────▼───────────────────────────────────┐
│ ENGINE  (Python CLI "sfal" + MCP server)                              │
│  sources: calendar · email · files · notes · imports · gbrain         │
│  normalize → evidence.json → candidates → validate → ledger → render   │
└───────┬──────────────────────────┬────────────────────────────┬───────┘
        │ reads                    │ reads                      │ writes (only)
  ORG RULE PACK              PERSONAL PROFILE              DATA FOLDER
  (versioned, shared)        (one per person)              ledger · cache · output
```

- **Engine** — all parsing, filtering, rule checks, ledger writes, rendering. Runs standalone from a terminal too.
- **MCP server** — exposes engine operations as tools so any MCP-capable host can drive it.
- **Skill / commands** — the human-in-the-loop workflow (§6). One `SKILL.md`, small per-host wrappers.
- **Safety lives in the engine** (§11), not in host-specific hooks; hooks are a second layer where the host supports them.

### Role of AI vs deterministic code
The AI (Cortex via OpenCode, or Claude) does **judgment and language**; the engine does everything that must be **exact and repeatable**.

| AI does | Engine does (deterministic) |
|---|---|
| Groups evidence into activities (meeting + prep deck + follow-up email = one activity) | Reads calendar, email, files, notes, imports |
| Chooses the activity type from the 22 definitions | Filters noise (cancelled, personal blocks, sync bursts, newsletters) |
| Writes Activity Hours Notes; suggests Solution Area | Matches accounts against the registry; applies routing rules |
| Resolves ambiguity (demo inside POC? internal or customer?) or marks `[to confirm]` | Computes hours (calendar durations only; else `[to confirm]`) |
| Extracts dated items from unstructured imports, quoting the source line | Dedupes against the ledger; consolidation keys |
| Fixes rows rejected by the validator | Validates every row against the rule pack |
| Translates review feedback ("merge 3 and 4, 2h prep") into engine operations | Writes the ledger (append-only); renders xlsx + md |
| Runs the setup interview; proposes the account registry | Enforces write boundary and review gate |

The AI never computes hours, never writes the ledger directly and cannot commit facts without evidence ids. Without the AI the engine still produces filtered, account-matched, rule-checked candidates; the user would pick types and write Notes manually.

### Engine components
| Component | Tech | Notes |
|---|---|---|
| `src_calendar` | Small compiled Swift helper (EventKit) → JSON | Recurrences expanded; RSVP, attendees, organizer, tz |
| `src_email` | `osascript` (AppleScript/JXA) driven from Python | Listed mailboxes only; metadata + short preview |
| `src_files` | Python `pathlib` + macOS metadata (`mdls`, xattrs) + Office core properties | Created/modified dates, author, downloaded-from, title |
| `src_notes` | Markdown reader | Per-customer activity notes, read-only |
| `src_imports` | `python-docx`, `openpyxl`, csv, plain text | Copilot / manual exports dropped in `inbox/` |
| `src_gbrain` | Via host's MCP | Context only; citations |
| `validate` | Python | Rule pack checks (§7) |
| `ledger` | Python, CSV + lock file | Append / void / supersede; only writer |
| `render` | `openpyxl` | xlsx (6 sheets) + md |

Python managed with `uv` (pinned deps); no system Python changes.

---

## 4. Evidence sources

Six sources, **each enabled or disabled by the user** (§4.8). Every source produces items in one common evidence format (`id, source, timestamp(s), title, people/domains, account_hint, kind, completeness, raw_ref`), so the rest of the pipeline never depends on which sources are on.

| # | Source | Read via | Produces activities? | Produces hours? |
|---|---|---|---|---|
| 1 | Calendar | EventKit | Yes — primary | Yes (exact) |
| 2 | Email | Mail.app automation | Yes (no-meeting work) | No — `[to confirm]`; may support prep |
| 3 | Project files | Folder scan + file metadata | Gap proposals only | No — `[to confirm]`; supports prep |
| 4 | Activity notes | Markdown, read-only | Yes | Only if the note states them |
| 5 | Imported documents | Files dropped in `inbox/` | Yes | Only if the document states them |
| 6 | GBrain | MCP | No — context only | No |

### 4.1 Calendar — EventKit
- Read all event calendars of the configured source (`Exchange`) for the window; recurring events expanded.
- Captured: start, end, duration, all-day, title, organizer, attendee count + domains, my RSVP, cancelled flag, location, recurrence flag, timezone.
- **Excluded automatically:** cancelled / "Canceled:" events; declined; all-day and holidays; personal blocks matching `ignore_titles` (e.g. "My Day Planning", "Lunch Time").
- **To-Confirm:** broadcast calls (attendees > `broadcast_threshold`, default 40); RSVP unknown and not confirmed by email.
- Overlapping events: hours counted once (most specific wins; the other flagged).

### 4.2 Email — Mail.app automation
- Reads **only the mailboxes the user lists** (`mailboxes`, default `["Sent Items"]`). No mail-folder-to-account mapping.
- Captured: date, subject, sender/recipient **domains**, thread key (normalized subject + participants), mailbox, attachment names, ≤300-char preview.
- **Dropped before the model sees anything:** `noreply`/notification senders, newsletters, auto-replies, internal broadcasts (> N recipients).
- Threads collapsed to one evidence item (first/last date, participants, attachments sent).
- **RSVP mails** ("Accepted:/Declined:/Tentative:") confirm calendar attendance; they are not activities.
- **Hours rule:** email-only activities get `activity_hours = [to confirm]`. Email may support prep hours for a calendar activity.
- Sync-coverage check: warn if the oldest synced message is newer than the period start.

### 4.3 Project files — scan + metadata
- Scan `workspace.root` for files **created or modified** in the window, excluding the data folder, the old `_ActivityLogging/`, temp/system files and `ignore` globs.
- **Signal strength per file:**
  - Office "last modified by" = owner → strong (authored by you); someone else → weak.
  - Downloaded file (macOS where-from / quarantine metadata) → **received**, not authored (e.g. RFP arrived).
  - Created in window → new work; modified only → edit/update.
- **Sync-burst filter:** ≥ `burst_min_files` files across ≥2 accounts with the same modified minute, or at `burst_times` → noise.
- **Work sessions:** files on the same account on the same day collapse to one evidence item.
- **Light content peek:** file name, folder, document title / first slide heading only — used to suggest a type (deck → 04/03, RFP compliance sheet → 06, POC folder → 09).
- **Two outcomes:**
  - Session within N days before/after a known activity on the same account → **prep (or follow-up) evidence** for that activity.
  - No matching activity from any other source → **gap proposal** ("worked on CONTOSO files 9–10 Oct, nothing logged") with hours `[to confirm]`, shown in its own review section.

### 4.4 Activity notes (optional)
- Per-customer activity notes (path glob); read-only; dated entries in window become evidence.

### 4.5 Imported documents — `inbox/`
For anything the user extracts manually, typically from **Copilot** (calendar summaries, email summaries) or by hand.
- Accepted formats: `.docx`, `.xlsx`, `.csv`, `.txt`, `.md`.
- The user drops files into `data_dir/inbox/`; each run reads files whose content falls in the window.
- **Tables** (docx/xlsx/csv): header-synonym column mapping (Date, Start/Time, End, Duration, Subject/Meeting, Organizer/From, Attendees/To, Account). Unrecognized layout → asked once, mapping remembered per file pattern.
- **Prose** (txt/md/docx without tables): the model extracts dated items; each must quote the source line it came from.
- Every imported item is marked `completeness: partial` (Copilot reports state they are subsets) and `kind: meeting | email | other`.
- **Dedupe vs live sources:** an imported meeting/email matching an EventKit/Mail item (same date, similar title, overlapping time) is merged, not duplicated; the live source wins on times.
- If the document states its own count ("25 meetings"), the parsed count is checked against it and a mismatch is warned.

### 4.6 GBrain (optional)
- Account context for accounts in play; used only for Notes wording and account disambiguation; every use cited in the evidence trail. Never a source of dates or hours.

### 4.7 Account resolution (all sources)
- The **account registry** in the profile (name, aliases, domains, kind = customer | partner) is the source of truth. Setup seeds it from project folder names, calendar attendee domains, sent-mail recipient domains and GBrain; the user confirms.
- Each evidence item is matched against the registry using all its text: every path segment + file name, email/attendee domains, subject/title keywords. Most specific match wins.
- Folder structure is an **optional hint**: if the user keeps one folder per customer (`workspace.account_folder_level`), that folder is weighted higher. Unstructured workspaces rely on keyword matching only.
- Partner + customer both matched → routing rules (§7.2) decide (e.g. `2024-NORTHWIND-TAILSPIN-…` → TAILSPIN, not NORTHWIND).
- No match or ambiguous → `[to confirm]`. Accounts are never guessed.

### 4.8 Enabling and disabling sources
- Each source has `enabled: true|false` in the profile (`sources:` block, §5). Setup asks which to turn on.
- Per-run override: `/sf-log last week --only calendar,email` or `--without files`.
- At least one activity-producing source (calendar, email, notes or imports) must be enabled; the run refuses otherwise.
- Disabled sources are listed in the run summary and on the xlsx Summary sheet, so the log states what it was built from.

---

## 5. Personal profile

One file per person: `~/.sf-activity-log/profile.yaml`, written by `/sf-log:setup` (interview + folder/mailbox scan + confirmation).

```yaml
owner: { name: "Lee, Sam", email_domain: mycompany.example }
timezone: Asia/Singapore
territory: [SG, MY]

data_dir: ~/Library/CloudStorage/OneDrive-MyCompany/Customers/_SFActivityLog
mirror_to: ~/Downloads                    # null to disable

workspace:
  root: ~/Library/CloudStorage/OneDrive-MyCompany/Customers
  account_folder_level: 2                 # optional hint: <Region>/<Account>/... ; null if unstructured
  ignore: ["_ActivityLogging/**", "_SFActivityLog/**", "~$*", "*.tmp", ".DS_Store"]

sources:                                  # turn any source on/off
  calendar:
    enabled: true
    eventkit_source: Exchange
    ignore_titles: ["My Day Planning", "Lunch Time"]
    broadcast_threshold: 40
  email:
    enabled: true
    account: Exchange
    mailboxes: ["Sent Items"]             # user lists exactly what to read, e.g. ["Sent Items", "Inbox"]
  files:
    enabled: false                        # example: this person does not want project files used
    burst_min_files: 4
    burst_times: []
    link_window_days: 3                   # prep/follow-up window around a known activity
  notes:
    enabled: true
    path: "*/*/_ActivityLogging/*.md"
  imports:
    enabled: true                         # Copilot / manual exports in data_dir/inbox/
  gbrain:
    enabled: true

# Account registry: the source of truth for account resolution.
# Aliases match path segments, file names, subjects and meeting titles (case-insensitive).
accounts:
  - { name: PROSEWARE, kind: customer, aliases: [PROSEWARE OMA], domains: [proseware.com, proseware.com.my] }
  - { name: WOODGROVE, kind: customer, domains: [woodgrove.com] }
  - { name: TAILSPIN, kind: customer }
  - { name: NORTHWIND, kind: partner }
  - { name: WINGTIP, kind: partner, domains: [wingtip-edge.com] }

policy_overrides:
  demo_inside_poc_logs_separately: true
```

---

## 6. Workflow

Commands (same names in every host):

| Command | Purpose |
|---|---|
| `/sf-log:setup` | First-run interview; writes profile; checks permissions |
| `/sf-log <period> [--only a,b] [--without c]` | Main run — `today`, `this week`, `last week`, `October`, `2026-10-06 to 2026-10-12`; optional source override |
| `/sf-log:confirm` | Work through the To-Confirm list |
| `/sf-log:void <entry_id> <reason>` | Void a row (append-only correction) |

### Run stages (`/sf-log <period>`)
1. **Resolve** period → `from..to` in profile timezone; create `run_id`.
2. **Collect** (engine): all **enabled** sources (profile, or `--only` / `--without` for this run) → `cache/<run_id>/evidence.json` (+ raw per source). Report counts and any coverage warnings.
3. **Pre-classify** (engine): exclusions, account matching, consolidation keys, dedupe against ledger → `candidates.json` with `new / extend / duplicate / excluded` marks.
4. **Propose** (model): group candidates into activities; choose activity type; draft Notes ("what was done, in detail"); set Solution Area; mark unknowns `[to confirm]`. Must cite evidence ids.
5. **Validate** (engine): rule pack checks (§7.4). Failures returned to the model to fix; loop until clean.
6. **Review gate** (user): table of New / Extended / Duplicate-skipped / **Possible unlogged work (file gaps)** / To-Confirm. User approves, edits or drops. **Nothing written before approval.**
7. **Commit** (engine): append rows; extensions = void old row + append superseding row with accrued hours.
8. **Render** (engine): xlsx + md to `output/`, mirror to Downloads; print totals, deltas vs previous run of this period, To-Confirm list.

---

## 7. Org rule pack (from logging guide v1.0)

Versioned file `rules/example-rules-1.0.yaml`. Every ledger row stores `rule_pack_version`.

### 7.1 Salesforce form fields (Paste-Ready order)
Account · Activity Type (REQ) · Opportunity (OPT; always for RFP/RFI, Value Review, POC/POV) · Reason (no opportunity) (mandatory if no opp) · Primary Owner (REQ) · Status (REQ) · Activity Date (REQ) · Activity Hours (REQ, > 0, excl. prep) · Prep Hours (OPT) · Activity Hours Notes (REQ) · Solution Area (OPT, multi).

### 7.2 Account routing
| Situation | Account |
|---|---|
| Customer exists | The customer |
| None / several customers / internal | **Example Corp (12345678)** |
| Partner enablement | The partner |
| Partner deal | The **customer**, not the partner |

### 7.3 Activity types (22, drop-down order)
01 Pipeline Generation · 02 Discovery Call · 03 Executive Briefing · 04 Technical Talk · 05 Technical Review · 06 RFP/RFI · 07 Product Demo · 08 Value Review · 09 POC/POV · 10 Support - Partner · 11 Support - Services · 12 Support - Customer Care · 13 Support - Marketing · 14 Support - Specialist Team · 15 Support - Peer · 16 Enablement - Partner · 17 Enablement - Customer · 18 Enablement - Internal · 19 Delivery - General · 20 Delivery - Quick Start · 21 Delivery - Outcome Tracking · 22 Team Administration.

### 7.4 Validator checks (hard = blocks commit; warn = shown in review)
| Check | Level |
|---|---|
| Activity type is one of the 22 | hard |
| Status ∈ Completed / In Progress / Planned / Cancelled | hard |
| Activity Hours > 0 (or `[to confirm]` → row held in To-Confirm, not paste-ready) | hard |
| Prep not included in Activity Hours (separate field) | hard |
| Account is not a partner when the activity is a partner deal | hard |
| No opportunity → Reason present (or `[to confirm]`) | hard |
| RFP/RFI, Value Review, POC/POV without opportunity | warn |
| One record per Value Review / POC-POV / RFP per account+opportunity — extend, don't duplicate | hard |
| Long-running record: Activity Date = latest date; Value Review Notes contain start & end dates | hard |
| Demo inside POC/POV logged as separate 07 (policy override) | hard |
| Quick Start: demos logged separately as 07 | hard |
| Environment prep for one demo → 07, not 22 | warn |
| Every hour value has ≥1 evidence id | hard |
| Names / dates without evidence → must be `[to confirm]` | hard |
| Solution Area ∈ AIOps / Discovery / ITSM / ESM / Other (+ detail in Notes) | hard |
| Primary Owner present | hard |

---

## 8. Ledger (25 columns)

`data_dir/ledger/ledger.csv` — UTF-8 CSV, append-only, single writer, lock file for OneDrive safety.

| # | Column | Meaning |
|---|---|---|
| 1 | `entry_id` | Stable id, e.g. `A0001` |
| 2 | `owner` | Primary Owner (from profile) |
| 3 | `account_name` | SF account per routing |
| 4 | `account_kind` | customer / partner / internal |
| 5 | `activity_type` | One of 22, e.g. `07 · Product Demo` |
| 6 | `opportunity` | Opp name/ID or blank (to-do) |
| 7 | `no_opp_reason` | Required if no opportunity |
| 8 | `status` | Completed / In Progress / Planned / Cancelled |
| 9 | `activity_date` | Delivery date (latest date for long-running) |
| 10 | `start_date` | First date for Value Review/POC/RFP, else = activity_date |
| 11 | `activity_hours` | Delivery hours, > 0 |
| 12 | `prep_hours` | Preparation hours |
| 13 | `notes` | SF "Activity Hours Notes" |
| 14 | `solution_area` | `;`-separated picklist values |
| 15 | `timezone` | IANA, e.g. `Asia/Singapore` |
| 16 | `evidence_refs` | Evidence ids (`cal:…`, `mail:…`, `file:…`, `note:…`) |
| 17 | `consolidation_key` | e.g. `POC|PROSEWARE|OMA` for accruing records |
| 18 | `rule_pack_version` | e.g. `example-1.0` |
| 19 | `voided` | true/false |
| 20 | `voided_by` | entry_id that replaced it, or `manual` |
| 21 | `supersedes` | entry_id this row replaces |
| 22 | `run_id` | Run that created the row |
| 23 | `to_confirm` | Open questions for this row |
| 24 | `confidence` | High / Medium / Low |
| 25 | `added_on` | ISO timestamp |

Active view = rows where `voided = false`. History is never deleted.

---

## 9. Folder layout

**Code (shareable repo)** — `~/Developer/sf-activity-log/`
```
engine/        Python package + CLI "sfal"
  sources/     calendar (Swift EventKit helper), email, files, notes, imports, gbrain
  rules/       example-rules-1.0.yaml + validator
  ledger.py · render.py · cli.py
mcp/           MCP server wrapping the engine
skill/         SKILL.md (shared workflow)
hosts/
  opencode/    commands + plugin (guard)
  claude-code/ plugin.json + commands + hook
tests/         fixtures (anonymised week) + one test per rule
docs/          getting-started/ · guides/ · reference/ · concepts/ · project/  (see docs/README.md)
```

**Data (per person)** — `data_dir`, default `Project/_SFActivityLog/`
```
ledger/ledger.csv
inbox/          imported documents: Copilot / manual exports (docx, xlsx, csv, txt, md)
cache/<run_id>/ evidence.json, candidates.json, proposal.json, validation.json, manifest.json
output/         Salesforce_Activity_Log_<from>_to_<to>.xlsx / .md
state.json      run history, open To-Confirm items
```

**Profile** — `~/.sf-activity-log/profile.yaml`

---

## 10. Output

Per-period folders: `output/<year>/<days|weeks|months|ranges>/<label>/` holding the latest
`.xlsx` (for the user, 6 sheets) and `.md` (for the AI), `runs.md`, `history/` and `.snapshot.json`.
The folder type is decided from the period's dates. Only the latest xlsx is copied to `mirror_to`.
**Full rules, prompt → folder examples and sheet contents: [Output reference](../reference/output.md).**

**Cadence:** weekly main run (Monday–Sunday) · optional daily capture · monthly rebuild to catch late evidence.

---

## 11. Guarantees and safety

- **Read-only sources:** calendar, mailbox, customer folders are never modified.
- **Write boundary:** engine refuses any write outside `data_dir` and `mirror_to`.
- **Single writer:** only `ledger.py` writes the ledger; append / void / supersede only.
- **Review gate:** no commit without explicit user approval in the session.
- **No fabrication:** validator rejects evidence-less facts; `[to confirm]` is the only placeholder.
- **Data minimisation:** email bodies never read beyond a short preview; noise dropped before the model.
- **Host hooks** (OpenCode plugin / Claude Code hook) add a second guard on direct ledger edits.

---

## 12. Colleague setup (Mac)

1. System Settings → Internet Accounts → add **Microsoft Exchange** (Calendars + Mail on).
2. Install: clone repo, `uv sync`, register the MCP server / commands in OpenCode.
3. Run `/sf-log:setup` — interview, folder & mailbox scan, account confirmation.
4. Approve the macOS prompts: **Calendars → Full Access** and **Automation → Mail** for the app running OpenCode.
5. Run `/sf-log last week` and review.

Target: under 15 minutes, documented on a one-page `SETUP.md`.

---

## 13. Build plan

| Phase | Scope | Exit criteria |
|---|---|---|
| 1 Engine core | Profile loader, EventKit collector, rule pack + validator, ledger, md render | Real week of calendar → validated rows → ledger |
| 2 More sources | Email (Mail.app) + filters, imports (`inbox/`), file scan + metadata + gap check, notes, account registry, source toggles | Same week enriched; email-only work and file gaps surfaced; any source can be switched off |
| 3 Deliverable | xlsx (6 sheets), Downloads mirror, deltas, To-Confirm | Paste-ready file for one week, user-verified in SF |
| 4 Hosts | MCP server, SKILL.md, OpenCode wrapper, then Claude Code wrapper, setup command | Full run from OpenCode + Cortex |
| 5 Pilot | Second presales engineer with a different folder structure | No code changes needed; only profile |
| 6 Release | Finalise docs (§16), version tag, colleague one-pager | A new user completes setup from `SETUP.md` alone |

Tests: anonymised fixture week with expected output; one test per §7.4 check; run on every change.

---

## 14. Deferred / to-do

- Seed ledger from existing Salesforce activities.
- Exact Salesforce account names (canonical account list).
- Opportunity linking, incl. quarter-end re-linking.
- Multi-owner records and team / manager roll-up.
- Windows support (imported documents as the calendar/email path).
- Microsoft 365 connector (Graph) when available.
- Microsoft Teams chats / ad-hoc calls (not in calendar) — no practical local access on Mac today.

## 15. Risks and open items

| Item | Mitigation |
|---|---|
| Exchange RSVP sometimes "unknown" in EventKit | Cross-check with Accepted/Declined emails; else treat as attended and show in review |
| Mail.app sync may not reach back to period start | Coverage check + warning |
| Cortex model behaviour with long tool workflows | Engine pre-classifies; model does small, bounded steps |
| OpenCode plugin / skill conventions | Verify against current OpenCode docs at Phase 4 |
| logging guide revisions | New rule pack version; rows keep the version they were validated under |

---

## 16. Documentation (deliverable)

Implemented in `docs/`, organised by purpose (getting started, guides, reference, concepts,
project) with short single-topic pages - see [docs/README.md](../README.md) and the docs rules in
[contributing](contributing.md). `reference/rules.md` is generated from the rule pack and the
validator; `tests/test_docs.py` keeps links, page length and coverage of checks, commands,
MCP tools and profile settings in sync with the code.
