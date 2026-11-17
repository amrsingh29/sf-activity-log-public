# Get started with Open Worker

> Use SF Activity Log in the Open Worker app, with Cortex as the model.
> About 10 minutes, once, if SF Activity Log is already set up in another tool.

**Before you start:** Open Worker installed and opened once, Cortex added as a model in Open
Worker, and **your work Outlook account added to macOS Calendar and Mail**. Python 3.11+ and Apple
Command Line Tools as in the [Goose CLI guide](goose-cli.md#2-install-the-basics).

> **Required, not optional:** the workflow reads your calendar and email through the macOS
> Calendar and Mail apps. Without your work Outlook account added there, the email part cannot work. See [step 1 of the Goose CLI guide](goose-cli.md#1-add-your-work-account-to-macos) for how.

## 1. Install

```bash
git clone https://github.com/amrsingh29/sf-activity-log-public.git ~/Developer/sf-activity-log
```

```bash
bash ~/Developer/sf-activity-log/hosts/openworker/install.sh
```

This installs the engine, adds six skills (`log-activity-note`, `sf-log`, `sf-log-setup`,
`sf-add-customer`, `sf-docs-sync`, `sf-docs-status`)
and registers the engine with Open Worker as two MCP servers: `sfal` for reading and preparing,
and `sfal-write` for the three tools that write (Open Worker asks you before each one).
Your other MCP servers are kept; the old file is saved as `mcp.json.bak`.

Quit and reopen Open Worker.

## 2. Set up your profile

Skip this if you already set up SF Activity Log in another tool - all tools share one
profile and one ledger. Otherwise, in a new Open Worker chat with Cortex: *"sf-log-setup"*.

On first use, allow Open Worker to access **Calendars (Full Access)** and to control **Mail**.

## 3. Capture a note, log your week

Open Worker has no slash commands. Ask in words - the skill loads when you ask for it:

| You type | What happens |
|---|---|
| *Log activity note: ACME demo went well, pricing due Friday* | Capture a note |
| *sf-log last week* | Log your week |
| *sf-log-setup* | Set up or change your profile |

Approve the save or commit when Open Worker asks. **You'll see:** the note path, or an Excel
file in Downloads - paste from **Paste-Ready**.

## Good to know

- The skills are written to load only when you ask for them. If one starts on its own, mute it
  for that chat in Open Worker and tell the maintainer.
- Keep Open Worker's sandbox off for these chats: the engine must read Calendar and Mail.
- To remove: delete the three folders in `~/.config/coworker/skills/` and the `sfal` and
  `sfal-write` entries in `~/.config/coworker/mcp.json`.

Next: [Capture a note](../use/capture-a-note.md) · [Log your week](../use/log-your-week.md)
