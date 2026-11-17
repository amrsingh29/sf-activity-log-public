# Configuration reference

One file per person: `~/.sf-activity-log/profile.yaml` (override with `$SFAL_PROFILE`).
The setup flow writes it for you; you can also edit it ([Update your profile](../use/update-your-profile.md)).
The engine validates it on every run.

Everything personal lives here. Shared rules (the logging guide) live in the rule pack, not here.

## Owner

```yaml
owner:
  name: "Lee, Sam"                   # REQUIRED. Salesforce Primary Owner, exactly as in Salesforce
  email: sam.lee@mycompany.example         # your main address
  aliases: [sam_lee@second.example]         # your other addresses (calendar invites often use them)
  email_domains: [mycompany.example, second.example]   # ALL company domains - these count as internal
timezone: Asia/Singapore             # IANA name; stored on every ledger row
```

You are recognised in invites if macOS flags you, **or** the address is `email`/`aliases`, **or**
the attendee name equals `owner.name`. Missing a company domain makes colleagues look like
customers, so list every one.

## Folders

```yaml
data_dir: ~/OneDrive/Customers/_SFActivityLog   # REQUIRED. ledger, cache, output, inbox
mirror_to: ~/Downloads                 # copy of the latest xlsx; null = no copy
workspace:
  root: ~/OneDrive/Customers           # your customer/project folder (files + notes sources)
  account_folder_level: 2              # optional hint: 2 = <Region>/<Account>/…, 1 = <Account>/…, null = unstructured
  internal_folders: [_Internal]        # work in these folders → Example Corp
  ignore: ["_SFActivityLog/*", "_ActivityLogging/*", "~$*", "*.tmp", ".DS_Store"]
```

The engine only **writes** inside `data_dir` and `mirror_to` (and `docs_mirror.output`, when on). `workspace.root` is read-only.
Output folder rules: [Output](output.md).

## Rule pack

```yaml
rules_pack: ~/my-rules.yaml            # optional; leave it out to use the bundled pack
```

The rule pack holds the activity types, account routing, statuses, solution areas and the form
order. To use your own, copy the bundled file (`src/sfal/rules/*.yaml`), edit it and point
`rules_pack` at it. `sfal doctor` reports a pack that cannot be read.

## Sources

Turn each on or off. A run can override for one time: `--only calendar,email` / `--without files`
(MCP: `only` / `without`). At least one of calendar, email, notes, imports must be on.

| Key | Default | Meaning |
|---|---|---|
| `sources.calendar.enabled` | true | macOS Calendar (EventKit) |
| `sources.calendar.eventkit_source` | Exchange | account name as shown in macOS Calendar |
| `sources.calendar.ignore_titles` | [] | personal blocks to drop; case-insensitive, `*` wildcards (`"lunch*"`) |
| `sources.calendar.broadcast_threshold` | 40 | more attendees than this → asked, not assumed |
| `sources.email.enabled` | false | macOS Mail (automation) |
| `sources.email.account` | Exchange | account name in Mail |
| `sources.email.mailboxes` | ["Sent Items"] | exactly which mailboxes to read |
| `sources.email.ignore_subjects` | [] | e.g. `["*pto*", "*leave*"]` |
| `sources.files.enabled` | false | scan of `workspace.root` |
| `sources.files.burst_min_files` | 4 | OneDrive sync burst: this many files in one minute across accounts |
| `sources.files.burst_times` | [] | minutes that are always sync noise, e.g. `["09:47"]` |
| `sources.files.link_window_days` | 3 | file work this close to an activity = its prep / follow-up |
| `sources.notes.enabled` | false | your Markdown activity notes |
| `sources.notes.path` | `**/_ActivityLogging/*.md` | glob under `workspace.root` |
| `sources.notes.save_to` | central | where `/log-activity-note` saves: `central` (`<data_dir>/notes/`) or `customer_folder` (`<customer folder>/_ActivityLogging/`, needs `workspace.root`) |
| `sources.imports.enabled` | false | Copilot / manual exports dropped in `<data_dir>/inbox/` |
| `sources.gbrain.enabled` | false | account context for the AI (never evidence) |

## Accounts (the registry)

The source of truth for matching evidence to Salesforce accounts.

```yaml
accounts:
  - { name: ACME Bank, kind: customer, aliases: [ACME, ACME-2026-RFP], domains: [acme.com] }
  - { name: Globex, kind: customer, domains: [globex.com] }
  - { name: Initech, kind: partner, domains: [initech.com] }
```

- `name`: exact Salesforce account name (rows must use it).
- `kind`: `customer` or `partner` - partner deals are routed to the customer automatically.
- `aliases`: other spellings found in folder names, titles, subjects (whole-word, case-insensitive).
- `domains`: email domains of that organisation.

No match, or more than one customer → the row is marked `[to confirm]`; the AI never guesses.
Start small; add accounts as they come up.

## Docs mirror

Optional, off by default. Text copies of Word, PowerPoint, PDF and some Excel files, so AI tools
and GBrain can search them ([Search your documents](../use/search-your-documents.md)).

```yaml
docs_mirror:
  enabled: false
  output: ~/.sf-activity-log/docs-mirror
  accounts: [ACME Bank, Globex]        # or [all]
  exclude_accounts: []                 # used with [all]
  include: [docx, pdf, pptx]
  excel_name_match: [rfp, compliance, requirement, clarification]
  max_size_mb: 20
  skip_folders: [Archive, Old, Drafts]
  extra_folders: []
  gbrain_import: false
  gbrain_source: docs
```

| Key | Default | Meaning |
|---|---|---|
| `docs_mirror.enabled` | false | turn the mirror on |
| `docs_mirror.output` | `~/.sf-activity-log/docs-mirror` | the only folder it writes to; refused inside OneDrive, `workspace.root`, `data_dir` or `extra_folders` |
| `docs_mirror.accounts` | [] | account names from the registry, or `[all]`. Chosen by name, not folder, so it works with any folder layout |
| `docs_mirror.exclude_accounts` | [] | left out when `accounts` is `[all]` |
| `docs_mirror.include` | [docx, pdf, pptx] | types always converted; add `xlsx` for every Excel file |
| `docs_mirror.excel_name_match` | [rfp, compliance, requirement, clarification] | Excel files whose name contains one of these are converted |
| `docs_mirror.max_size_mb` | 20 | larger files are skipped |
| `docs_mirror.skip_folders` | [Archive, Old, Drafts] | folder names never entered (any level, case-insensitive) |
| `docs_mirror.extra_folders` | [] | folders outside `workspace.root`; the folder's own name counts for the account |
| `docs_mirror.gbrain_import` | false | after each sync, commit the copies to a local git repo in `output` and run `gbrain sync` for them; a GBrain problem never fails the sync. Without GBrain on the Mac, syncs never mention it |
| `docs_mirror.gbrain_source` | docs | the GBrain source id; register it once and give your AI tools access ([Search your documents in GBrain](../use/search-documents-in-gbrain.md)) |

Each file's account comes from the registry above, the same way as for every source. Files that
match no account, or only a partner, are not copied and are counted in the report.

## Policy overrides

```yaml
policy_overrides:
  demo_inside_poc_logs_separately: true   # a demo inside a POC/POV is its own 07 · Product Demo row
```
