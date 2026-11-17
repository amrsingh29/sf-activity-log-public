# AI hosts

The engine knows nothing about AI tools. Every host drives the same engine in one of two ways:

| Route | What the AI uses | Used by |
|---|---|---|
| **MCP** | 18 `sfal_*` tools from the `sfal-mcp` server (stdio) | Goose (recipes); Claude Code; Open Worker; omp; Hermes; any MCP host |
| **CLI** | `~/.sf-activity-log/bin/sfal` in a shell, JSON output | OpenCode (command + skill) |

The workflow instructions are one file, `skill/SKILL.md`, written for both routes. The MCP
server serves it as its instructions; Goose recipes and the OpenCode skill are generated/copied
from it at install time. **Change the workflow only in `skill/SKILL.md`, then re-run the installers.**

The safety rules are in the engine, so they hold in every host: approval code required to commit,
append-only ledger, writes only inside `data_dir`/`mirror_to`.

## MCP tools

| Tool | Purpose |
|---|---|
| `sfal_doctor` | profile + source access check |
| `sfal_rules` | 22 types, routing, statuses, solution areas |
| `sfal_profile_show` | read the profile |
| `sfal_resolve_period` | period text → dates + output folder type |
| `sfal_prepare` | collect + pre-classify evidence |
| `sfal_validate` | save + validate a proposal; returns review table and approval code |
| `sfal_commit` | write to the ledger (needs the approval code) |
| `sfal_render` | build the period's xlsx + md |
| `sfal_read_output` | read a period's Markdown log |
| `sfal_ledger` | ledger rows |
| `sfal_setup_scan` | propose a profile from folders, calendar, sent mail |
| `sfal_setup_save_profile` | validate + save the confirmed profile |
| `sfal_account_add` | add one customer or partner and its folder (plan, then apply after a yes) |
| `sfal_ask` | ask this run's `decisions` as one interactive form (takes just `run_id`) |
| `sfal_note_context` / `sfal_note_detail` / `sfal_note_targets` / `sfal_note_save` | activity notes: a day's items, full detail, where to save, save |
| `sfal_catalog` | rebuild the catalog page; it also rebuilds after every note save, commit and render |

Errors return `{"ok": false, "error": "…"}` instead of failing the call.

### How each host asks questions
| Host | Tool | Looks like |
|---|---|---|
| OpenCode | its built-in question tool | tabs, arrow-key choices, "type your own" |
| Goose | `sfal_ask` → MCP elicitation | one prompt per item, named after it, default in [brackets] (Enter keeps it); Skip / Log / Hours or s / l / h; then a details box |
| Claude Code | `sfal_ask` if it shows the form, else `decisions_text` | a form, or the compact table in chat |
| anything else | `decisions_text` in chat | compact table; reply "ok" or "1 log, 5 log 1h" |

The decisions (which items, options, default) come from the engine, so the questions are the
same in every host. `sfal_ask` works with both MCP protocol generations (classic mid-call request,
and the 2026 "input required" round trip Goose uses). If a host cannot show forms, the AI falls
back to `decisions_text`.

## Goose

Install: see [Get started](../README.md#start-here).

- Recipes in `~/.config/goose/recipes/`: **`log-activity-note`** (optional `what`), **`sf-log`** (parameter `period`) and **`sf-log-setup`**.
  Each loads only the `sfal` MCP extension - no shell, no other tools.
- **Goose Desktop** lists them under **Recipes** - press ▶ ([Get started with Goose Desktop](../start/goose-desktop.md)).
- **Terminal** (interactive, so you can review and approve):
  ```bash
  goose run --recipe sf-log --params period="last week" -s
  goose run --recipe sf-log-setup -s
  ```
- The Desktop app and the terminal are separate apps for macOS: each needs its own Calendar and
  Mail permission, and the Desktop app does not read `~/.zshrc`.
- Model: whatever Goose is configured with (`active_provider`). Use the company provider (Cortex).

## OpenCode

Install: see [Get started](../README.md#start-here).

- Commands `/log-activity-note`, `/sf-log <period>` and `/sf-log-setup` in `~/.config/opencode/commands/`; uses the CLI route.
- The workflow files are `~/.sf-activity-log/SKILL.md` and `NOTE.md`, read by those commands. It is deliberately
  **not** installed as an OpenCode skill: skills can be auto-loaded whenever a request looks
  related, and the workflow must run only when you ask for it.
- Optional: OpenCode can also use the MCP route by adding to `opencode.json`:
  ```json
  "mcp": { "sfal": { "type": "local", "command": ["~/.sf-activity-log/bin/sfal-mcp"], "enabled": true } }
  ```
  (use the full path; the skill then prefers the `sfal_*` tools).

## Claude Code

Install: [Get started with Claude Code](../start/claude-code.md) (`hosts/claude-code/install.sh`).

- Same command files as OpenCode in `~/.claude/commands/`, plus `disable-model-invocation: true`:
  Claude Code otherwise offers commands to the model as skills, and the workflow must run only
  when you type it.
- Registers `sfal-mcp` at user scope (`claude mcp add --scope user sfal ...`); the commands prefer
  the `sfal_*` tools and fall back to the CLI.
- Model: Claude. What the workflow reads goes to **Anthropic, not Cortex** - see
  [Safety](safety.md#your-data-stays-with-the-company-ai).

## Open Worker

Install: [Get started with Open Worker](../start/openworker.md) (`hosts/openworker/install.sh`).

- Open Worker uses Anthropic-format skills (`SKILL.md`) and MCP, like Claude - not slash commands.
  Six skills in `~/.config/coworker/skills/` point to `~/.sf-activity-log/` workflow files (`SKILL.md`, `NOTE.md`, `DOCS.md`).
- It loads a skill when the AI judges it relevant, so each description says "use ONLY when the
  user explicitly asks". Muting a skill per chat is the fallback.
- The engine is registered twice in `~/.config/coworker/mcp.json`: `sfal` (read and prepare, no
  prompt) and `sfal-write` (`sfal_commit`, `sfal_note_save`, `sfal_setup_save_profile`, `sfal_account_add`, each
  approved in Open Worker first) - on top of the engine's own approval code.
- Model: whatever the chat uses; pick Cortex. Questions arrive as a form if Open Worker shows MCP
  forms, else as the compact table in chat.

## omp (oh-my-pi)

Install: [Get started with omp](../start/omp.md) (`hosts/omp/install.sh`).

- Slash commands like OpenCode: the same three command files, copied to `~/.omp/agent/commands/`
  (`$ARGUMENTS` is filled in the same way). They run only when typed.
- The engine is the `sfal` MCP server in `~/.omp/agent/mcp.json`; omp treats MCP tools as
  "write" tier, so the workflow also runs in omp's `write` approval mode.
- Model: any omp provider; Cortex is a `cortex` provider in `~/.omp/agent/models.yml`
  (`cortex-fast`, `cortex-max`).

## Hermes Agent

Install: [Get started with Hermes](../start/hermes.md) (`hosts/hermes/install.sh`).

- Every Hermes skill is also a slash command, so the six skills in
  `~/.hermes/skills/sf-activity-log/` give `/log-activity-note`, `/sf-log`, `/sf-log-setup`,
  `/sf-add-customer`, `/sf-docs-sync` and `/sf-docs-status`.
- Each skill is generated at install: a short header from `hosts/hermes/skills/` plus the full
  text of `skill/NOTE.md` or `skill/SKILL.md`, so it works without reading another file.
- Hermes lists skills for the AI too; the descriptions say "only when the user types it".
- The engine is the `sfal` MCP server under `mcp_servers` in `~/.hermes/config.yaml`.

## Adding another host

1. If it supports MCP: register `~/.sf-activity-log/bin/sfal-mcp` as a stdio server and give it
   the text of `skill/SKILL.md` (most hosts read the server instructions automatically).
2. If it only has a shell: give it `skill/SKILL.md` as instructions; it uses the CLI route.
3. Add `hosts/<name>/` with an install script, following `hosts/goose/` or `hosts/opencode/`, then
   add it to `hosts/install-all.sh` (detected by its settings folder), the Makefile and a
   `docs/start/<name>.md` page.

After any workflow or engine change, `make install` (`hosts/install-all.sh`) updates every tool found
on the Mac in one go; Claude Code only when SF Activity Log is already set up there (`--with-claude` to add it).
