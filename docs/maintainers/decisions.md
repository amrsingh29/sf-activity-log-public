# Decisions

Record of design decisions and why. New decisions are appended with a date.

## Agreed 2026-10-14 (design sign-off)

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


## 2026-10-14 (phase 1 build)
| # | Decision | Rationale |
|---|---|---|
| D18 | Python venv instead of `uv` for now | `uv` not installed; `pyproject.toml` stays uv-compatible |
| D19 | Engine path fixed at `~/.sf-activity-log/bin/sfal` (symlink) | Same instructions for every user and every AI host |
| D20 | Commit requires the approval code from the last successful validate | Proposal cannot change between the user's review and the write |
| D21 | Hours the user confirms are cited as `user:<words>` evidence | Keeps every hour traceable, including user-supplied ones |
| D22 | voided/voided_by are the only fields changed after a row is written; all ops in `audit.log` | Append-only history with visible corrections |

## 2026-10-14 (phase 2 build)
| # | Decision | Rationale |
|---|---|---|
| D23 | Downloaded = Spotlight `kMDItemWhereFroms`; OneDrive quarantine flag ignored | OneDrive sets quarantine on synced files, which marked the user's own decks as received |
| D24 | Office "last modified by" = you wins over download origin | Your edited copy of a received file is your work |
| D25 | File sessions grouped by matched account (not folder level) | Customers nested under partner folders (e.g. WINGTIP/FABRIKAM) got merged |
| D26 | Note activity date = date in title/activity line, else note date | Notes are often written days after the event |
| D27 | An RSVP email applies to the matching occurrence on its date or the next one | A single-occurrence decline must not hide the rest of a recurring series |
| D28 | Imported meetings matching a calendar meeting (same day, ≥60% title words) are merged; calendar wins | Copilot exports repeat what EventKit already has, with less precise times |
| D29 | File work never creates rows by itself; gaps are review questions | File dates cannot show what was done or for how long |

## 2026-10-14 (phase 3 build)
| # | Decision | Rationale |
|---|---|---|
| D30 | Output organised per **period**, not per run; per-run data stays in `cache/<run_id>/` | Users think in "the log for week 41"; repeated runs of a period must not create look-alike folders |
| D31 | Folder type from the dates only (day / Mon–Sun week / calendar month / range), under the start year | Same dates always land in the same folder however they were typed |
| D32 | Excel for the user, Markdown for the AI; only the xlsx goes to Downloads | User works in Excel; AI reads Markdown reliably |
| D33 | Changed re-render archives the previous version to `history/`; unchanged re-render overwrites | Keeps history without clutter |

## 2026-10-14 (phase 4 build)
| # | Decision | Rationale |
|---|---|---|
| D34 | Goose instead of Claude Code as the second host | Company AI (Cortex) runs in Goose; no Claude contract |
| D35 | MCP server as the host-neutral interface; CLI kept | MCP is Goose's native integration and works in most hosts; fixed tool schemas suit weaker models; no shell access needed |
| D36 | One `api.py` behind both CLI and MCP | Identical behaviour, one place to fix |
| D37 | One host-neutral `SKILL.md`; recipes/skill generated from it | No drift between hosts |
| D38 | Goose recipes load only the sfal extension | Least privilege: no shell or file tools in the logging session |
| D39 | Owner recognised by macOS flag, email, alias or name; all company domains internal | A second company address (second.example) was treated as another person and an external domain |
| D40 | Setup proposes from the user's data; saves only after explicit confirmation, keeping a backup | Fast onboarding without guessed accounts |

## 2026-10-14 (explicit invocation)
| # | Decision | Rationale |
|---|---|---|
| D41 | OpenCode: workflow file outside the skills folder; only `/sf-log` and `/sf-log-setup` read it | Auto-loaded skills triggered the workflow alongside an unrelated command |

## 2026-10-15 (Log Activity Note)
| # | Decision | Rationale |
|---|---|---|
| D42 | Daily capture command named `/log-activity-note` | Clear action, no clash with the old `/activity-log` or `/sf-log` |
| D43 | Notes saved centrally by default; customer folders opt-in | Many people have no folder per customer |
| D44 | Account in the note header; folder only a fallback | Works for any folder structure |
| D45 | AI picks the account, the engine maps account → folder; write allowed only to central notes or a matched `_ActivityLogging/` | Keeps the AI's judgment without letting it choose arbitrary paths |

## 2026-11-05 (Docs mirror, issue #3)
| # | Decision | Rationale |
|---|---|---|
| D46 | Docs mirror lives in SF Activity Log as a separate, optional module (off by default) | The profile already knows the workspace, the accounts and their aliases; one install for SEs. Logging never depends on it |
| D47 | Accounts chosen by registry name, not folder path | Same config for every colleague whatever their folder layout; survives reorganising |
| D48 | Output outside OneDrive, the workspace and `data_dir`; refused otherwise | Read-only on customer folders; no sync clutter; search tools (GBrain) write marker files into what they import |
| D49 | SF Activity Log only produces the folder; it does not run GBrain | No dependency on one search tool; the user's nightly job runs the import |
| D50 | Protection respected: encrypted Office files, password PDFs and PDFs that forbid copying text are skipped; PDFs that open without a password and allow copying are read | Many vendor guides are "encrypted" with no real restriction; real restrictions are never worked around |
| D51 | Online-only files are skipped, not downloaded; a copy made while the file was local is kept | Avoid surprise downloads of large folders |
| D52 | Removing more than half of the copies at once is held unless `--rebuild` | A missing folder or profile mistake must not wipe the mirror |
| D53 | Unassigned and partner-only files are not copied; counted in the report only with `accounts: [all]` | Keeps the mirror per account; the fix is an alias, not a catch-all folder |
| D54 | Chat workflow in a new `skill/DOCS.md`; `SKILL.md` and `NOTE.md` unchanged | Owner-controlled files stay as they are (AGENTS.md rule 5) |
| D55 | Optional `gbrain_import` (off by default) replaces D49's manual step: the mirror is a local git repo, each sync commits, then runs `gbrain sync` | `gbrain import` cannot run while the shared `gbrain serve` holds the database lock; `gbrain sync` hands the work to the running server but reads git. Off by default so colleagues without GBrain are unaffected; failures are reported and retried, never fatal |
| D56 | Agents show the profile lines to add and never offer to edit the profile | The profile decides what is read; changes go through the user or an engine command that confirms first |

## 2026-11-17 (Going public)
| # | Decision | Rationale |
|---|---|---|
| D57 | The public repo is a separate, scrubbed copy of the private development repo, published as one commit per release. The private repo stays private and keeps the full history | The old history held personal email addresses, a named colleague's interview notes and real customer names. Hiding files with `.gitignore` does not remove them from history, and a history rewrite is a force-push that cannot be undone and leaves hidden pull-request references behind |
| D58 | Real names are replaced by one fixed fictional name each, from a private rules file, in the copy only; the private repo is never changed by publishing | Tests, docs and examples stay consistent with each other; the same real name always maps to the same fictional one, in the same alphabetical order |
| D59 | A release stops unless the tests pass on the copy (installed in a fresh virtualenv) and a scan of the copy is clean; pushing needs a typed confirmation | The copy must work for a new user, and a name that slips past the replacements must be caught before it is public |
| D60 | Public commits use a neutral author; the push is refused if the clone's remote is the private repo or any commit carries another email | Personal addresses must not appear in the public history |
| D61 | In the public copy the company's internal logging guide is named generically ("internal logging guide") and its internal account number is replaced by a made-up one | The guide and the number are the employer's internal material; the tool works the same with generic wording and an example number |
| D62 | The public edition ships a generic example rule pack (same numbers, behaviour and checks, invented names and wording); the company's real pack stays in the private repo. A profile setting `rules_pack` lets anyone load their own pack from a file | The rule pack is the company's internal guide in machine form; renaming it (D61) was not enough, the content itself must not be published. D62 replaces D61 where they differ |
