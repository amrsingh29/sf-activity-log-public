# Get started with Goose CLI

> From nothing to your first note and your first weekly log, in the terminal.
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
brew install python block-goose-cli
```

## 3. Store your Cortex key

```bash
security add-generic-password -U -a "$USER" -s cortex-api-key -l "Cortex API key" -w
```

Paste the key at the hidden prompt (asked twice). Then make it available to the terminal:

```bash
echo 'export CORTEX_API_KEY="$(security find-generic-password -a "$USER" -s cortex-api-key -w 2>/dev/null)"' >> ~/.zshrc && source ~/.zshrc
```

The key itself never goes in a file - only the Keychain.

## 4. Connect Goose to Cortex

```bash
mkdir -p ~/.config/goose/custom_providers && cat > ~/.config/goose/custom_providers/custom_cortex.json <<'EOF'
{
  "name": "custom_cortex", "engine": "openai", "display_name": "Cortex",
  "api_key_env": "CORTEX_API_KEY",
  "base_url": "https://cortex.mycompany.example/v1/chat/completions",
  "models": [{ "name": "cortex-fast", "context_limit": 262144 }],
  "supports_streaming": true, "requires_auth": true
}
EOF
```

```bash
goose configure
```

Choose **Configure Providers → Cortex → cortex-fast**. Check it:

```bash
goose run --no-session -t "Reply with exactly: GOOSE OK"
```

## 5. Install SF Activity Log

```bash
git clone https://github.com/amrsingh29/sf-activity-log-public.git ~/Developer/sf-activity-log
```

You can clone it anywhere; the examples use `~/Developer/sf-activity-log`. After installing,
the tools always find it through `~/.sf-activity-log/bin/sfal`.

```bash
bash ~/Developer/sf-activity-log/hosts/goose/install.sh
```

**You'll see:** `valid: log-activity-note`, `valid: sf-log`, `valid: sf-log-setup`.

## 6. Set up your profile

```bash
goose run --recipe sf-log-setup -s
```

It scans your folders, calendar and sent mail, interviews you one topic at a time, and saves
when you say yes. When macOS asks about your terminal app, allow **Full Access** to Calendars and
**OK** to control Mail.

## 7. Capture your first note

```bash
goose run --recipe log-activity-note --params what="ACME demo went well, pricing due Friday" -s
```

Check the note and say **y**. [More](../use/capture-a-note.md)

## 8. Log your first week

```bash
goose run --recipe sf-log --params period="last week" -s
```

Answer the questions (Enter keeps the default; `l`, `s` or a time like `45m`), check the review
table, type **approve**. **You'll see:** an Excel file in Downloads - paste from **Paste-Ready**.

Quieter output: `goose configure` → Goose Settings → Tool Output → **Low**.
Keychain password prompts that fail: [Troubleshooting](../troubleshooting.md#goose).

Next: [Capture a note](../use/capture-a-note.md) · [Log your week](../use/log-your-week.md)
