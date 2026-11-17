# Get started with Claude Code

> Use SF Activity Log in Claude Code instead of (or next to) your Cortex tools.
> About 10 minutes, once. Follow the steps in order.

**Before you start:** a Mac (macOS 14+), **your work Outlook account added to macOS Calendar and
Mail**, Claude Code installed, and access to the code repository.

> **Required, not optional:** the workflow reads your calendar and email through the macOS
> Calendar and Mail apps. Without your work Outlook account added there, the email part cannot work.

**Privacy - read first.** In Goose, OpenCode, omp, Hermes and Open Worker with Cortex, what the
workflow reads (meeting titles, attendees, email subjects and - for notes - email text) goes only
to the company AI (Cortex).
In Claude Code it goes to **Anthropic**. Check your company's policy before using it with
customer data.

## 1. Add your work account to macOS

System Settings → **Internet Accounts** → **Add Account** → **Microsoft Exchange**. Sign in with
your work email and turn on **Calendars** and **Mail**.

## 2. Install

```bash
git clone https://github.com/amrsingh29/sf-activity-log-public.git ~/Developer/sf-activity-log
```

```bash
bash ~/Developer/sf-activity-log/hosts/claude-code/install.sh
```

This installs the engine, adds `/log-activity-note`, `/sf-log`, `/sf-log-setup` and `/sf-add-customer` to
`~/.claude/commands/`, and registers the `sfal` MCP server. The commands run only when you type
them - Claude never starts them on its own.

**You'll see:** `Then in a new Claude Code session: /sf-log last week`.

## 3. Set up your profile

Start a new Claude Code session and type `/sf-log-setup`. Skip this if you already set up SF
Activity Log in another tool - all tools share one profile and one ledger.

Allow the macOS prompts for your terminal app (Calendars **Full Access**, control Mail **OK**).

## 4. Capture a note, log your week

```text
/log-activity-note ACME demo went well, pricing due Friday
```

```text
/sf-log last week
```

Questions appear as a form or as plain text in the chat - answer, check the review table, type
**approve**. **You'll see:** an Excel file in Downloads - paste from **Paste-Ready**.

## Update or remove

After pulling a new version, run the installer again. To remove:

```bash
claude mcp remove --scope user sfal && rm ~/.claude/commands/{log-activity-note,sf-log,sf-log-setup,sf-add-customer}.md
```

Next: [Capture a note](../use/capture-a-note.md) · [Log your week](../use/log-your-week.md)
