# Troubleshooting

> Find your symptom, apply the fix. Start with the health check below.

The health check tests every enabled source:

```bash
~/.sf-activity-log/bin/sfal doctor
```

## Calendar

| Symptom | Fix |
|---|---|
| "Calendar Full Access not granted" | System Settings → Privacy & Security → Calendars → set your terminal (or Goose) to **Full Access** |
| "No calendars for source 'Exchange'" | Add the Exchange account (Internet Accounts), or set `sources.calendar.eventkit_source` to the name `doctor` lists |
| Recurring meetings missing | Open the Calendar app once so it syncs |
| Colleagues treated as customers | Add every company domain to `owner.email_domains` |

## Email

| Symptom | Fix |
|---|---|
| "Mail automation not allowed" | System Settings → Privacy & Security → Automation → enable **Mail** for your terminal |
| "mailbox … not found" | Use the exact folder name shown in the Mail app (e.g. `Sent Items`) |
| "oldest synced message is …" warning | Mail has not downloaded older mail yet - open Mail and let it sync, or accept partial email evidence |

## Goose

| Symptom | Fix |
|---|---|
| Keychain password prompt that will not accept your password | `echo 'export GOOSE_DISABLE_KEYRING=1' >> ~/.zshrc`, open a new terminal |
| "missing required key CORTEX_API_KEY" | Your AI key is not set in this shell - check `~/.zshrc` |
| Long JSON printed before the questions | `goose configure` → Goose Settings → Tool Output → **Low** |
| Recipe not found | Re-run `hosts/goose/install.sh` |

## Goose Desktop

| Symptom | Fix |
|---|---|
| Recipes not listed | Run `hosts/goose/install.sh`, then quit and reopen Goose |
| Keychain password prompt that will not accept your password | See below |
| Calendar or Mail access denied in the app | System Settings → Privacy & Security → Calendars / Automation → allow **Goose** (separate from your terminal) |
| A recipe edit disappeared | The installer regenerates recipes - change the workflow in the repo (`skill/SKILL.md`) instead |

**Keychain prompt in Goose Desktop.** If the "login" keychain password is out of sync with your
Mac password, give Goose the key without the keychain. The app does not read `~/.zshrc`, so set
both values for apps started from the Dock, then quit and reopen Goose:

```bash
launchctl setenv GOOSE_DISABLE_KEYRING 1
```

```bash
launchctl setenv CORTEX_API_KEY "$(zsh -ic 'echo $CORTEX_API_KEY')"
```

These last until the Mac restarts. The permanent fix is to resync the keychain password
(Keychain Access, or IT).

## Other AI tools

| Symptom | Fix |
|---|---|
| Commands or skills missing after an update | `make install` in the repo (or `bash hosts/install-all.sh`), then restart the tool |
| Claude Code: `/sf-log` not listed | `bash hosts/claude-code/install.sh`, then start a new session |
| omp: `sfal` not connected | In omp, `/mcp test sfal`; servers connect a moment after startup |
| Hermes: skills or `sfal` missing right after installing | Quit and reopen Hermes - its background gateway reloads the config a few seconds later; `hermes mcp test sfal` |
| Open Worker: skill starts when you did not ask | Mute the skill for that chat and tell the maintainer |

## Results look wrong

| Symptom | Fix |
|---|---|
| Many accounts `[to confirm]` | Add those accounts and domains to your profile |
| A meeting is missing | Check it is not cancelled, declined, all-day, or in `ignore_titles` |
| A Copilot export adds nothing | Its dates may be outside the period, or it has no date column ([Use exports](use/use-exports.md)) |
| Excel says it needs repair | Re-run the period; if it repeats, report it with the file |
| "approval code does not match" | The proposal changed after the review; the AI must validate again and show you the new table |

## Where to look

| What | Where |
|---|---|
| Every action taken on the ledger | `<log folder>/ledger/audit.log` |
| Evidence of a run | `<log folder>/cache/<run_id>/` |
| Builds of a period | `runs.md` in the period's output folder |
