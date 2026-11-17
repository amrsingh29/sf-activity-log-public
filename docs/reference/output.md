# Output reference

Everything the tool produces for you lives in `<data_dir>/output/`. This page explains **where a
run's files go, why, and how the period you type in the prompt changes that**.

## 1. Layout

```
<data_dir>/
├── output/                                   ← deliverables (this page)
│   └── <year>/
│       ├── days/<YYYY-MM-DD>/
│       ├── weeks/<ISO-year>-W<nn>_<from>_to_<to>/
│       ├── months/<YYYY-MM>_<MonthName>/
│       └── ranges/<from>_to_<to>/
├── catalog/index-modern.html                 ← every note, record and period in one page (rebuilt automatically)
├── cache/<run_id>/                           ← per-run evidence trail (machine side)
├── ledger/ledger.csv                         ← single source of truth
├── note-ids.json                             ← every place each note has lived, so moved notes stay logged
└── inbox/                                    ← imported documents you drop in
```

Every **period folder** has the same contents:

| File | For | What it is |
|---|---|---|
| `Salesforce_Activity_Log_<from>_to_<to>.xlsx` | **you** | Latest version, 6 sheets (below). Also copied to `mirror_to` (e.g. Downloads). |
| `Salesforce_Activity_Log_<from>_to_<to>.md` | the AI / quick reading | Latest version, same content as Markdown. Not copied to Downloads. |
| `runs.md` | audit | One line per render: when, which committed runs, records, hours, what changed. |
| `history/` | audit | Earlier versions, named `…_<YYYY-MM-DD_HHMMSS>.xlsx/.md`; `…_legacy.md` = files moved from the old flat layout. |
| `.snapshot.json` | the engine | Rows of the latest version, used to compute the deltas. Do not edit. |

## 2. How the prompt decides the folder

You type a period (`/sf-log last week`, `/sf-log October`, …). The engine turns it into a
**from–to date range**, and the **dates alone** decide the folder type — not the words you typed.

| Rule | Folder type | Example folder |
|---|---|---|
| from = to (a single day) | `days` | `2026/days/2026-10-14` |
| from is a Monday and to is the Sunday 6 days later | `weeks` | `2026/weeks/2026-W41_2026-10-05_to_2026-10-11` |
| from is the 1st and to is the last day of the same month | `months` | `2026/months/2026-10_October` |
| anything else | `ranges` | `2026/ranges/2026-10-01_to_2026-10-03` |

The **year folder** is the year the period starts in. The week number is the ISO week
(Monday-based), so a week spanning New Year keeps the start year's folder:
`2026/weeks/2026-W53_2026-12-28_to_2027-01-03`.

### Prompt examples (today = Wed 14 Oct 2026)

| You type | Resolves to | Goes to |
|---|---|---|
| `today` | 2026-10-14 | `2026/days/2026-10-14` |
| `yesterday` | 2026-10-13 | `2026/days/2026-10-13` |
| `2026-10-07` | 2026-10-07 | `2026/days/2026-10-07` |
| `this week` | 2026-10-12 → 2026-10-18 | `2026/weeks/2026-W42_2026-10-12_to_2026-10-18` |
| `last week` | 2026-10-05 → 2026-10-11 | `2026/weeks/2026-W41_2026-10-05_to_2026-10-11` |
| `2026-10-05 to 2026-10-11` | same dates | **same week folder** as `last week` |
| `this month` / `October` | 2026-10-01 → 2026-10-31 | `2026/months/2026-10_October` |
| `last month` / `September` | 2026-09-01 → 2026-09-30 | `2026/months/2026-09_September` |
| `November` (a future month name) | the most recent November: 2025-11 | `2025/months/2025-11_November` |
| `last 7 days` | 2026-10-08 → 2026-10-14 | `2026/ranges/2026-10-08_to_2026-10-14` |
| `2026-10-06 to 2026-10-12` | Tue → Mon | `2026/ranges/…` (not Mon–Sun, so not a week) |

Supported period words: `today`, `yesterday`, `this week`, `last week`, `this month`,
`last month`, `last N days`, `<month> [year]`, `YYYY-MM-DD`, `YYYY-MM-DD to YYYY-MM-DD`.
If the AI is unsure what you meant, it asks before running.

## 3. Running the same period again

| Situation | What happens |
|---|---|
| First render of a period | Folder created; `runs.md` says "first version"; Deltas sheet says "first version". |
| Re-render, ledger unchanged | Files overwritten in place; nothing goes to `history/`; `runs.md` line says "no change". |
| Re-render after changes (new rows, corrections, extended POC/Value Review/RFP) | Previous `.xlsx`/`.md` moved to `history/` with their timestamp; new version written; Deltas sheet and `runs.md` show per-customer changes. |

## 4. Overlapping periods (day, week, month)

A day, its week and its month all show the same activities — each folder is **a view of the one
ledger**, not a separate log. Nothing is logged twice: the commit step refuses evidence already
in the ledger (check C16). So you can run days during the week, the week on Friday and the month
at month end; the month file always shows the complete month.

Long-running records (Value Review, POC/POV, RFP/RFI) appear in every period their start–latest dates
overlap.

## 5. The Excel workbook (6 sheets)

| Sheet | Content |
|---|---|
| Summary | Period, owner, generated time, rule pack, sources used; records ready / held; activity and prep hours; totals by type and by account |
| Paste-Ready | Ready records only, columns in Salesforce form order: Account, Activity Type, Opportunity, Reason (no opportunity), Primary Owner, Status, Activity Date, Activity Hours, Prep Hours, Activity Hours Notes, Solution Area |
| Period Ledger | Every active record in the period (incl. held), all 25 ledger columns |
| Per-Customer Deltas | Per account: records and hours before vs now, change, status (new / changed / removed / unchanged) and details (added, removed, "A0003 replaced by A0013") |
| To-Confirm | Held records (hours, account or no-opportunity reason still `[to confirm]`) with the open questions |
| Evidence Trail | Each record → every piece of evidence behind it (source, date, title, ref) |

"Held" records are in the ledger but not on Paste-Ready until their `[to confirm]` items are resolved.

## 6. What goes to Downloads

Only the latest `.xlsx` of the period you just rendered is copied to `mirror_to`
(default `~/Downloads`). Nothing reads it back; delete it after pasting. Set `mirror_to: null`
in the profile to turn the copy off.

## 7. Moving from the old flat layout

Files from v0.1/v0.2 (`output/Salesforce_Activity_Log_<from>_to_<to>.md`) are moved
automatically, the first time any period is rendered, into their period folder's `history/`
as `…_legacy.md`.
