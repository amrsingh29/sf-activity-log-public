# Get started with omp

> Use SF Activity Log in omp (oh-my-pi), the terminal coding agent, with Cortex as the model.
> About 10 minutes, once, if SF Activity Log is already set up in another tool.

**Before you start:** omp installed and run once, Cortex configured as an omp provider (a
`cortex` entry in `~/.omp/agent/models.yml`, key from the Keychain), and **your work Outlook
account added to macOS Calendar and Mail**. Python 3.11+ and Apple Command Line Tools as in the
[Goose CLI guide](goose-cli.md#2-install-the-basics).

> **Required, not optional:** the workflow reads your calendar and email through the macOS
> Calendar and Mail apps. Without your work Outlook account added there, the email part cannot work. See [step 1 of the Goose CLI guide](goose-cli.md#1-add-your-work-account-to-macos) for how.

## 1. Install

```bash
git clone https://github.com/amrsingh29/sf-activity-log-public.git ~/Developer/sf-activity-log
```

```bash
bash ~/Developer/sf-activity-log/hosts/omp/install.sh
```

This installs the engine, adds `/log-activity-note`, `/sf-log` and `/sf-log-setup` to
`~/.omp/agent/commands/` (the same files as OpenCode), and registers the engine as the `sfal`
MCP server in `~/.omp/agent/mcp.json`. Your other MCP servers are kept; the old file is saved
as `mcp.json.bak`. The commands run only when you type them.

## 2. Set up your profile

Skip this if you already set up SF Activity Log in another tool - all tools share one profile
and one ledger. Otherwise start `omp` and type `/sf-log-setup`.

On first use, allow your terminal app to access **Calendars (Full Access)** and to control **Mail**.

## 3. Capture a note, log your week

```text
/log-activity-note ACME demo went well, pricing due Friday
```

```text
/sf-log last week
```

Pick the Cortex model with `--model cortex/cortex-fast` (or `cortex/cortex-max`), or make it
your default in `~/.omp/agent/config.yml`. Answer the questions, check the review table, type
**approve**. **You'll see:** an Excel file in Downloads - paste from **Paste-Ready**.

## Good to know

- omp's default approval mode runs tools without asking. The engine's own approval code still
  guards the ledger: nothing is logged until you approve the review table.
- To remove: delete the three files in `~/.omp/agent/commands/` and the `sfal` entry in
  `~/.omp/agent/mcp.json`.

Next: [Capture a note](../use/capture-a-note.md) · [Log your week](../use/log-your-week.md)
