# Contributing

For whoever maintains the tool.

## Setup

```bash
cd ~/Developer/sf-activity-log
python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests
```

## Layout

```
src/sfal/
  api.py            every operation - shared by CLI and MCP
  cli.py            `sfal` command (thin)
  mcp_server.py     `sfal-mcp` server (thin) + sfal_ask
  prepare.py        collect → cross-source steps → candidates + decisions
  sources/          calendar, email, notes, files, imports
  decisions.py      what the user must decide, with defaults
  validate.py       checks C01–C21 (CHECKS list)
  ledger.py         the only ledger writer
  render.py         Excel + Markdown, period folders, history, deltas
  setup.py          setup scan + save
  rules/            rule pack (logging guide)
skill/SKILL.md      the AI workflow - one file for every host
hosts/              installers: goose/, opencode/
scripts/gen_docs.py generates docs/reference/rules.md
docs/               these docs
tests/              unittest suite
```

## Common changes

| Change | Do |
|---|---|
| logging guide updated | new `src/sfal/rules/example-rules-<v>.yaml`, bump `version`, run `scripts/gen_docs.py` |
| New or changed check | edit `validate.py` and its `CHECKS` entry, add a test, run `scripts/gen_docs.py` |
| New profile setting | add to `profile.py` `DEFAULTS` and the template, document in `docs/reference/configuration.md` |
| New source | `src/sfal/sources/<name>.py` with `collect()`, register in `prepare.py`, document in `docs/reference/sources.md` |
| Workflow wording | edit `skill/SKILL.md` (or `skill/NOTE.md`), then `make install` - it updates every AI tool found on the Mac |
| New AI host | see [AI hosts](../understand/ai-tools.md#adding-another-host) |
| AI tool setup changed (Goose, OpenCode, Claude Code, Open Worker, omp, Hermes, Cortex key) | update that tool's page in `docs/start/` (and `docs/use/change-cortex-key.md`) - adapted from the team's *ai-system-setup-guides* |

## Docs rules

Structure (Diátaxis - one purpose per folder):

| Folder | Purpose | Rule |
|---|---|---|
| `docs/start/` | quickstart per AI tool | one continuous page, zero to first weekly log, no detours |
| `docs/use/` | how-to, in the order of the user's week | task title; numbered steps; per-tool table; "You'll see" |
| `docs/reference/` | exact facts | complete and dry; `rules.md` generated |
| `docs/understand/` | explanation | why, not steps |
| `docs/troubleshooting.md`, `docs/faq.md` | by symptom / by question | short answers that link to the details |
| `docs/maintainers/` | design, decisions, changelog, contributing | may be long |

Page template for `start/` and `use/`: `# Title` → `> one-line purpose` → **Before you start** →
steps → **You'll see** → `Next:` links. Per-tool steps always as one table with two columns, *Tool · Type this*, and one row per tool
(Goose Desktop, Goose CLI, OpenCode, Claude Code, omp, Hermes, Open Worker), so no tool is buried.

Words: the product is **SF Activity Log**; its jobs are **Capture a note** (daily) and
**Log your week** (weekly); "log folder" in user pages (`data_dir` only in reference).
Second person, short sentences, one action per step. Fictional examples only (ACME Bank, Globex,
Initech, Nina Patel). Pages under 160 lines. Never edit `docs/reference/rules.md` by hand - run
`scripts/gen_docs.py`.

`tests/test_docs.py` checks links, page length, the index, the template, the generated rules
page, coverage of checks / commands / MCP tools / profile settings, and real names.

## Before committing

```bash
.venv/bin/python scripts/gen_docs.py
.venv/bin/python -m unittest discover -s tests
```

Record notable changes in [changelog](changelog.md) and design choices in [decisions](decisions.md).
