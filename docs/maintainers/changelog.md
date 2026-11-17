# Changelog

## Unreleased
- Licence: MIT (`LICENSE`), copyright held by "SF Activity Log contributors"; declared in `pyproject.toml`
  (build now needs setuptools 77 or later) and linked from the README.
- Rule pack choice: new profile setting `rules_pack` (a path to your own rule pack file); `sfal doctor`
  reports a pack that cannot be read. Without it the bundled pack is used. The public edition of this
  project ships a generic example pack, so a company supplies its own rules (decision D62).
- README redesigned: the problem and the two habits, a flow diagram of a weekly run, who-does-what,
  an architecture diagram (both Mermaid, rendered by GitHub), a worked example, where your data goes
  per AI tool, three quickstart steps and a docs map.
- Docs: every start page now says, in bold and in a note, that your work Outlook account must be added
  to macOS Calendar and Mail (the email part cannot work without it). The README links to
  "How it works" in the top bar and in the Documentation section.
- Public releases are cut from a private development repo as a scrubbed copy, one commit per
  release (decisions D57-D60). The copy is tested in a fresh virtualenv and scanned before
  anything is pushed.
- Catalog: `sfal catalog` now writes `catalog/index-modern.html`, the modern page (theme switch, back
  navigation, evidence on records), built from `src/sfal/catalog_modern.html` with the owner's name and
  the data filled in. It replaces `index.html`, which is no longer written. Checked in headless Chrome
  with no script errors.
- Docs mirror (optional, off by default): `sfal docs sync` / `sfal docs status`, `sfal_docs_sync` /
  `sfal_docs_status`, and `/sf-docs-sync` / `/sf-docs-status` for every AI tool (workflow in
  `skill/DOCS.md`). Converts Word, PowerPoint, PDF and name-matched Excel files of the accounts chosen
  in `docs_mirror.accounts` into Markdown copies with a header pointing to the original. Account by
  registry match, so any folder layout works. Only changed files are converted; copies of deleted,
  moved or deselected files are removed (more than half at once is held unless `--rebuild`). Never
  writes inside OneDrive or the workspace; protected files are skipped, online-only files are not
  downloaded. New dependency: pypdf. New page `use/search-your-documents.md`.
  Optional `docs_mirror.gbrain_import`: each sync commits the copies to a local git repo in the mirror
  folder and runs `gbrain sync` (works while GBrain's server runs); failures are reported and retried.
  New page `use/search-documents-in-gbrain.md`: register the source once, give each AI tool read
  access, keep it current, when to repeat, troubleshooting and undo.
- Add a customer: `sfal account-add` / `sfal_account_add` and `/sf-add-customer` (Goose recipe, OpenCode,
  Claude Code, omp, Hermes, Open Worker). Plans first: it asks for a missing name or country, shows the
  account entry and the folder to create or reuse, and writes only after a yes. Backs up the profile,
  appends the account (existing accounts are kept), creates `<country>/<name>/_ActivityLogging/` and any
  extra folders, and never changes an existing folder or file. Refuses a name or alias already in use.
  Open Worker puts it on the approval-gated `sfal-write` server. New page `use/add-a-customer.md`.
- `make install` / `hosts/install-all.sh` updates every AI tool found on the Mac (Goose, OpenCode,
  Open Worker, omp, Hermes; Claude Code only when already set up or with `--with-claude`).
  Docs brought up to date for all six tools (FAQ, glossary, architecture, how-to tables, Cortex key).
- Hermes Agent host: `hosts/hermes/install.sh` (`make install-hermes`) - three skills (Hermes makes each
  a slash command), generated with the full workflow text, and the engine as the `sfal` MCP server in
  `~/.hermes/config.yaml` (added once, backup kept). New page `start/hermes.md`. Tested in Hermes with Cortex.
- omp (oh-my-pi) host: `hosts/omp/install.sh` (`make install-omp`) - the OpenCode command files in
  `~/.omp/agent/commands/` and the engine as the `sfal` MCP server in `~/.omp/agent/mcp.json`
  (merged). New page `start/omp.md`. Tested end to end in omp with Cortex.
- Notes keep their identity when moved or renamed: new notes carry a `note-id`; older notes are
  known by their creation stamp and title, else file name; `<data_dir>/note-ids.json` remembers
  every path id a note has had, so records logged before a move still match (no double logging,
  C16 still refuses). Copies with the same identity fall back to path ids.
- Open Worker host: `hosts/openworker/install.sh` (`make install-openworker`) - three Anthropic-format
  skills (explicit use only) and the engine as two MCP servers (`sfal` read, `sfal-write` approval-gated);
  merges `~/.config/coworker/mcp.json`. New page `start/openworker.md`. MCP 1.30 client verified
  against the server; an end-to-end run in the app is still to do.
- Docs: new page `understand/architecture.md` - the layers, module map, a weekly run as a
  sequence, what a run leaves on disk, where the safety lives and how to extend it. States which
  writers go through `safety.check_writable` and which deliberately do not. Linked from the docs
  index.
- Catalog: `sfal catalog [--open]` / `sfal_catalog` build `<data_dir>/catalog/index-modern.html` (formerly `index.html`) - every
  activity note (customer folders + central), ledger record and rendered period, searchable, with
  an Accounts timeline, follow-ups and *not logged yet* badges. Rebuilt after every note save,
  commit and render; read-only; no AI. New page `use/browse-the-catalog.md`. Records sort by any
  column; colours match the StoryForge gallery. Calendar tab: month grid of notes and records per
  day with daily and weekly hours, day view, agenda list on small screens.
- Workflow: questions asked with a form end with "or type your changes in the message box"
  (Claude's form shows buttons only).
- Claude Code host: `hosts/claude-code/install.sh` (`make install-claude`) installs the engine,
  the three commands with `disable-model-invocation: true` (explicit use only) and the `sfal`
  MCP server. New page `start/claude-code.md`; privacy exception (Anthropic, not Cortex) in
  safety, FAQ and SECURITY.md.
- Repository layout: README header and table of contents, AGENTS.md, CONTRIBUTING.md,
  SECURITY.md, issue and pull request templates, CI, Makefile.

## 0.5.3 — 2026-10-15 (documentation restructure)
- Docs reorganised by reader need (Diátaxis): `start/` one continuous quickstart per AI tool
  (tool setup, Cortex key, install, profile, first note, first weekly log); `use/` task guides in
  the order of the week (Capture a note, Log your week, fix, re-run, exports, profile, Cortex key);
  `reference/` (new: note format); `understand/` (loop + example); top-level troubleshooting and
  new FAQ; `maintainers/` for design, decisions, changelog, contributing.
- One page template for start and use pages, checked by the docs tests; consistent naming.

## 0.5.2 — 2026-10-15 (note safeguards)
- User-stated hours need the user's own words (`hours_quote`); the note shows them
  ("1 h (you said: …)").
- Mix-up check: an activity that resembles a same-day meeting it does not cite is refused until
  the meeting is cited or confirmed different (`not_meetings`).
- OpenCode `AGENTS.md` activity-notes rule replaced by a pointer to `/log-activity-note`
  (backup kept) so only one workflow writes notes.

## 0.5.1 — 2026-10-15 (note quality)
- Notes now match the old per-customer note standard: summary; per activity what, context,
  discussed, outcomes and decisions, next steps, people (with RSVP); follow-ups; cited background;
  "To confirm" list. Batch input, one note per customer.
- New `note-detail` / `sfal_note_detail`: invite description and attendee RSVPs (calendar now reads
  the invite text), full email bodies of the thread with boilerplate and quoted history removed.
- Engine-checked hours: an activity's duration must equal its meeting, else `[to confirm]` or
  user-stated (`hours_source: user`).
- File names `YYYY-MM-DD_HHMM_<topic>_activity-note.md`, slug cut at a word boundary;
  internal work saved to the internal folder.

## 0.5.0 — 2026-10-15 (Log Activity Note)
- New **`/log-activity-note`** (OpenCode) / **Log Activity Note** recipe (Goose): capture a note
  while it is fresh from your words + the day's meetings, mail and files; asks at most 2
  questions; saves after you confirm.
- Notes saved **centrally** (`<data_dir>/notes/`, default) or into the matched **customer folder**
  (`_ActivityLogging/`, opt-in via `sources.notes.save_to`). The engine maps account → folder via
  the registry; the AI never picks a path. Never overwrites.
- Notes carry `account:` in their header; the weekly run trusts it. The notes source now reads the
  central folder and customer folders, and works without `workspace.root`.
- Engine: `note-context`, `note-targets`, `note-save` (CLI) and `sfal_note_*` (MCP).
- Setup suggests the save mode; notes enabled by default for new profiles.

## 0.4.4 — 2026-10-14
- OpenCode: the workflow is no longer installed as an auto-loadable skill (it was being pulled
  in by unrelated activity-logging requests). It lives at `~/.sf-activity-log/SKILL.md` and runs
  only via `/sf-log` or the new `/sf-log-setup` command. The installer removes the old skill.

## 0.4.3 — 2026-10-14 (docs per AI tool)
- **Agent setup** (`docs/agent-setup/`): one page per AI tool - Goose Desktop, Goose CLI,
  OpenCode - plus the shared Cortex API key page, adapted from the team's setup guides;
  `scripts/save-cortex-api-key.sh` included.
- **Getting started per tool**: prerequisites page, then one install + profile + first-week page
  each for Goose Desktop, Goose CLI and OpenCode. Replaces the shared install / first-run pages
  and the separate Goose Desktop guide.
- Goose Desktop keychain workaround moved to Troubleshooting.

## 0.4.2 — 2026-10-14 (documentation)
- Docs reorganised by purpose: getting-started (overview, install, first run), guides (weekly
  routine, answering questions, fix a record, re-run a period, exports, profile, troubleshooting),
  reference (configuration, sources, rules, output, commands, ledger, glossary), concepts (how it
  works with a worked example, AI and engine, safety, hosts), project (design, decisions,
  changelog, contributing). Short single-topic pages, fictional examples.
- `docs/reference/rules.md` generated from the rule pack and validator (`scripts/gen_docs.py`);
  validator checks listed in `validate.CHECKS`.
- `tests/test_docs.py`: links, page length, index coverage, generated page current, every check /
  command / MCP tool / profile setting documented, no real customer names in user docs.
- Removed unused profile setting `territory`.

## 0.4.1 — 2026-10-14 (interaction)
- Engine-built `decisions` in prepare: each flagged item with options and a default
  (declined, not on invite, broadcast, overlap, tentative, no RSVP, email-only, hours not stated,
  file gap) + `decisions_text` (plain one-line-reply table).
- `sfal_ask` MCP tool: asks all decisions in one interactive form via MCP elicitation, on both
  protocol generations (2026 input-required round trip used by Goose, and classic).
- `already_logged_summary` with engine totals - the AI no longer adds up hours.
- Skill: ask via host question tool → `sfal_ask` → `decisions_text`; terminal-friendly output rules.
- 73 tests.

## 0.4.0 — 2026-10-14 (phase 4: hosts + setup)
- **MCP server** `sfal-mcp` (stdio) with 12 `sfal_*` tools; errors returned as `{ok:false}`;
  serves `skill/SKILL.md` as its instructions.
- **Goose**: recipes `sf-log` (period parameter) and `sf-log-setup`, generated from the skill;
  each loads only the sfal extension. Installer `hosts/goose/install.sh`.
- **Setup**: `setup_scan` proposes owner, aliases, company domains, folder structure, account
  candidates, customer/partner domains and personal blocks from folders, calendar and sent mail;
  `setup_save_profile` validates and saves (with backup). Setup interview in the skill.
- **Owner aliases**: you are recognised by flag, email, alias or name - fixes a second company
  address (e.g. second.example) being treated as another person / external domain.
- `api.py`: one implementation shared by CLI and MCP. Skill is host-neutral (MCP or CLI).
- Docs: CONFIGURATION.md (every profile key), HOSTS.md (OpenCode, Goose, adding a host).
- 68 tests.

## 0.3.0 — 2026-10-14 (phase 3: deliverable)
- **Excel workbook** per period with 6 sheets: Summary, Paste-Ready (Salesforce form order, numeric
  hours), Period Ledger (25 columns), Per-Customer Deltas, To-Confirm, Evidence Trail.
- **Period folders**: `output/<year>/<days|weeks|months|ranges>/<label>/`, type decided from the
  period's dates (`period.classify`). Rules and prompt examples in `docs/OUTPUT.md`.
- **Versions**: unchanged re-render overwrites in place; changed re-render moves the previous
  version to `history/` with its timestamp. `runs.md` logs every render; `.snapshot.json` drives deltas.
- Only the latest `.xlsx` is copied to `mirror_to`; the `.md` stays for the AI.
- Old flat `output/*.md` files are moved to their period's `history/` as `…_legacy.md`.
- 60 tests.

## 0.2.0 — 2026-10-14 (phase 2: more sources)
- **Email** (Mail.app automation): only the listed mailboxes; one item per thread per day; drops
  no-reply senders, auto-replies, mass mail (>25 recipients), `ignore_subjects`; inline images ignored;
  sync-coverage warning. RSVP replies confirm/contradict calendar attendance (`accepted_by_email`,
  `declined_by_email`) on the matching occurrence.
- **Imported documents** (`<data_dir>/inbox/`: docx, xlsx, csv, txt, md): header-synonym tables,
  dated prose lines, in-document de-duplication, stated-count check, merge into matching calendar meetings.
- **Activity notes**: one note = one item. Activity date: frontmatter `activity-date`, else an
  `Activity date:` field, else a date in the title, else the note date. Inline fields separated by
  `·` are read (e.g. `**Duration:** 3.0 h`).
- **Project files**: created/modified in period, Office author check, download origin (Spotlight
  where-from; OneDrive quarantine ignored), sync-burst filter, sessions per matched account per day,
  title peek; linked to nearby activities (`prep_for` / `follow_up_of`) or flagged `gap`.
- Account matching uses all item text + folder hint; `workspace.internal_folders` → Example Corp
- Validator counts stated hours of untimed items (notes/imports).
- `doctor` checks every enabled source; skill reports sources and warnings first; new review section
  "Possible unlogged work".
- Dates: day-first numeric with dashes (`08-10-2026`); overlapping matches resolved.
- 52 tests.

## 0.1.0 — 2026-10-14 (phase 1: engine core)
- Engine CLI `sfal`: `doctor`, `profile init|show`, `rules`, `prepare`, `validate`, `commit`, `render`, `ledger`.
- Calendar source via macOS EventKit (compiled Swift helper, recurrences expanded); noise filters
  (cancelled, declined, all-day, personal blocks) and flags (broadcast, RSVP unknown, prep, demo, overlap).
- Account registry with domain/keyword matching and partner-deal → customer routing.
- Rule pack `example-1.0` from the logging guide v1.0; validator checks C01–C21.
- Append-only ledger (25 columns) with extend/void, audit log, lock file; approval code required to commit.
- Markdown deliverable with Paste-Ready (Salesforce form order), To-Confirm, Evidence Trail; Downloads mirror.
- Write boundary: engine writes only in `data_dir` and `mirror_to`.
- Shared `SKILL.md`; OpenCode command `/sf-log` and installer.
- 36 engine tests.
