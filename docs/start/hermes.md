# Get started with Hermes

> Use SF Activity Log in Hermes Agent, with Cortex as the model.
> About 10 minutes, once, if SF Activity Log is already set up in another tool.

**Before you start:** Hermes installed and run once with Cortex as its model, and **your work
Outlook account added to macOS Calendar and Mail**. Python 3.11+ and Apple Command Line Tools as
in the [Goose CLI guide](goose-cli.md#2-install-the-basics).

> **Required, not optional:** the workflow reads your calendar and email through the macOS
> Calendar and Mail apps. Without your work Outlook account added there, the email part cannot work. See [step 1 of the Goose CLI guide](goose-cli.md#1-add-your-work-account-to-macos) for how.

## 1. Install

```bash
git clone https://github.com/amrsingh29/sf-activity-log-public.git ~/Developer/sf-activity-log
```

```bash
bash ~/Developer/sf-activity-log/hosts/hermes/install.sh
```

This installs the engine, adds six skills under `~/.hermes/skills/sf-activity-log/` and
registers the engine as the `sfal` MCP server in `~/.hermes/config.yaml` (once; a backup of the
file is kept). In Hermes every skill is also a slash command: `/log-activity-note`, `/sf-log`,
`/sf-log-setup`, `/sf-add-customer`, `/sf-docs-sync` and `/sf-docs-status`. Each skill carries
the full workflow text; re-run the installer after an update.

## 2. Set up your profile

Skip this if you already set up SF Activity Log in another tool - all tools share one profile
and one ledger. Otherwise start `hermes` and type `/sf-log-setup`.

On first use, allow your terminal app to access **Calendars (Full Access)** and to control **Mail**.

## 3. Capture a note, log your week

```text
/log-activity-note ACME demo went well, pricing due Friday
```

```text
/sf-log last week
```

Answer the questions, check the review table, type **approve**. **You'll see:** an Excel file in
Downloads - paste from **Paste-Ready**.

## 4. Make your documents searchable (optional)

```text
/sf-docs-sync dry run
```

```text
/sf-docs-sync
```

Set `docs_mirror` in your profile first: [Search your documents](../use/search-your-documents.md).
Commands and options are in [Commands](../reference/commands.md).

## Good to know

- Hermes also shows skills to the AI, which can load one when it seems relevant. The skills say
  "only when the user types it", and nothing is logged without your approval either way.
- Hermes can run on chat apps (Telegram, Slack and others). Use these skills in the terminal: on a
  chat app, your meeting and email text would pass through that app.
- To remove: delete `~/.hermes/skills/sf-activity-log/` and the `sfal` entry under `mcp_servers`
  in `~/.hermes/config.yaml`.

Next: [Capture a note](../use/capture-a-note.md) · [Log your week](../use/log-your-week.md)
