# AGENTS.md - rules for AI coding agents

Read this before changing anything in this repository. It applies to every coding agent
(OpenCode, Goose, Claude Code, Cursor, ...). Maintainer details:
[docs/maintainers/contributing.md](docs/maintainers/contributing.md).

## Hard rules

1. **Nothing is logged without approval.** Never weaken or bypass the approval code:
   `commit` must re-validate and refuse on a mismatch. No shortcut, flag or test helper that
   writes ledger rows without it.
2. **The ledger is append-only.** `ledger.py` is the only writer. Corrections void and
   supersede; rows are never deleted or edited in place. Every action goes to `audit.log`.
3. **Nothing is invented.** Unknowns stay `[to confirm]`; user-stated hours need the user's own
   words (`hours_quote`). Do not add defaults that fill facts the evidence does not support.
4. **The engine does facts, the AI does judgment.** Dates, hours, checks, account matching and
   totals belong in `src/sfal/` - never in workflow instructions.
5. **The workflow files are owner-controlled.** `skill/SKILL.md` and `skill/NOTE.md` change only
   when the owner asks for that change. Otherwise suggest the edit (current text → proposed text)
   and leave the file alone. Shortening `SKILL.md` is deferred (issue #2).
6. **Explicit invocation only.** Workflows run only when the user types the command or runs the
   recipe. Never install them where a host auto-loads them (for example OpenCode's skills folder).
7. **Fictional names only** in user docs, `skill/`, `hosts/` and tests: ACME Bank, Globex,
   Initech, Nina Patel. `tests/test_docs.py` enforces it.
8. **Never touch the user's data**: `~/.sf-activity-log/profile.yaml`, the log folder
   (`data_dir`), the ledger, customer folders and any older logging pipeline. Tests use fixtures
   and temp profiles only.

## Keep docs in step

- `docs/reference/rules.md` is generated - run `make docs`, never edit by hand.
- New check, command, MCP tool or profile setting → document it; the docs test fails otherwise.
- `start/` and `use/` pages follow the page template; pages stay under 160 lines; every page is
  linked from `docs/README.md`.

## Layout

See the layout block in [docs/maintainers/contributing.md](docs/maintainers/contributing.md#layout).

## Workflow

```bash
make docs       # regenerate docs/reference/rules.md
make test       # unittest suite, ~3 s, no Mail/Calendar access needed
make install    # engine + every AI tool found on the Mac (hosts/install-all.sh)
make doctor     # environment and profile check
```

Every change: docs regenerated, tests pass, changelog entry, then commit.
