# Get started with OpenCode

> From nothing to your first note and your first weekly log, in OpenCode.
> About 30 minutes, once. Follow the steps in order.

**Before you start:** a Mac (macOS 14+), **your work Outlook account added to macOS Calendar and
Mail**, a Cortex API key, and access to the code repository (ask the owner to add your GitHub account).

> **Required, not optional:** the workflow reads your calendar and email through the macOS
> Calendar and Mail apps. Without your work Outlook account added there, the email part cannot work. Step 1 shows how.

## 1. Add your work account to macOS

System Settings → **Internet Accounts** → **Add Account** → **Microsoft Exchange**. Sign in with
your work email and turn on **Calendars** and **Mail**.

## 2. Install the basics

[Homebrew](https://brew.sh) needed:

```bash
xcode-select --install
```

```bash
brew install python opencode
```

Check `opencode --version` shows **v2**.

## 3. Store your Cortex key

```bash
security add-generic-password -U -a "$USER" -s cortex-api-key -l "Cortex API key" -w
```

Paste the key at the hidden prompt (asked twice). Then:

```bash
echo 'export CORTEX_API_KEY="$(security find-generic-password -a "$USER" -s cortex-api-key -w 2>/dev/null)"' >> ~/.zshrc && source ~/.zshrc
```

## 4. Connect OpenCode to Cortex

Save as `~/.config/opencode/opencode.json` (merge into it if the file exists):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "cortex/cortex-fast",
  "providers": {
    "cortex": {
      "name": "Cortex", "env": ["CORTEX_API_KEY"], "package": "@ai-sdk/openai-compatible",
      "settings": { "baseURL": "https://cortex.mycompany.example/v1" },
      "models": { "cortex-fast": { "name": "Cortex Fast",
        "capabilities": { "tools": true, "input": ["text", "image"], "output": ["text"] },
        "limit": { "context": 262144, "output": 65536 } } }
    }
  }
}
```

Restart OpenCode's background server so it picks up the key, then check:

```bash
opencode service stop; opencode run "Reply with exactly: CORTEX OK"
```

## 5. Install SF Activity Log

```bash
git clone https://github.com/amrsingh29/sf-activity-log-public.git ~/Developer/sf-activity-log
```

You can clone it anywhere; the examples use `~/Developer/sf-activity-log`. After installing,
the tools always find it through `~/.sf-activity-log/bin/sfal`.

```bash
bash ~/Developer/sf-activity-log/hosts/opencode/install.sh
```

This adds `/log-activity-note`, `/sf-log` and `/sf-log-setup`. They run only when you type them.

## 6. Set up your profile

Start `opencode`, then type `/sf-log-setup`. It scans your folders, calendar and sent mail,
interviews you one topic at a time, and saves when you say yes. Allow the macOS prompts for your
terminal app (Calendars **Full Access**, control Mail **OK**), and allow OpenCode to run
`~/.sf-activity-log/bin/sfal` when it asks.

## 7. Capture your first note

```text
/log-activity-note ACME demo went well, pricing due Friday
```

Check the note and say **y**. [More](../use/capture-a-note.md)

## 8. Log your first week

```text
/sf-log last week
```

Answer the questions (tabs; arrow keys; Enter), check the review table, type **approve**.
**You'll see:** an Excel file in Downloads - paste from **Paste-Ready**.

Do not install the OpenCode desktop app yet - it is v1 and breaks v2 data. The browser UI is
fine: `opencode service start`, then `opencode pair`.

Next: [Capture a note](../use/capture-a-note.md) · [Log your week](../use/log-your-week.md)
