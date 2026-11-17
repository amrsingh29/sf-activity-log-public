# Search your documents in GBrain

> Put the text copies of your documents into GBrain, so every AI tool you use can find them.
> You set it up once; after that every sync keeps GBrain up to date by itself.

## Before you start

- The docs mirror is on and has run at least once ([Search your documents](search-your-documents.md)).
- GBrain is installed and its shared server (`gbrain serve`) runs on your Mac.
- At least one AI tool is connected to GBrain.

No GBrain? Skip this page. The mirror works without it and never mentions GBrain.

## How it fits together

Two separate permissions decide what an AI tool can search:

| Step | What it means | How often |
|---|---|---|
| Register the source | GBrain learns the mirror folder exists, as a source called `docs` | Once per Mac |
| Give agents access | Each AI tool is allowed to read the `docs` source | Once per AI tool |

An AI tool sees only the sources it was given. Registering `docs` without giving access means
the copies are in GBrain but no tool can find them.

## 1. Turn on GBrain updates

Add one line under `docs_mirror` in `~/.sf-activity-log/profile.yaml`:

```yaml
docs_mirror:
  enabled: true
  accounts: [ACME Bank]
  gbrain_import: true
```

## 2. Sync once

| Tool | Type this |
|---|---|
| Goose Desktop | Recipes → **SF Activity Log - Sync Documents** |
| Goose CLI | `goose run --recipe sf-docs-sync -s` |
| OpenCode, Claude Code, omp, Hermes | `/sf-docs-sync` |
| Open Worker | ask *"sf-docs-sync"* |

This turns the mirror folder into a local git repo, which is what GBrain reads. The repo has no
remote and is never pushed.

The sync will say GBrain was not updated and show a `gbrain sources add` command. That is
expected the first time.

## 3. Register the source (once)

In Terminal:

```bash
gbrain sources add docs --path ~/.sf-activity-log/docs-mirror --name "Docs mirror" --federated
```

`--federated` puts the copies into your normal GBrain searches, next to your other sources.
This works while the GBrain server is running.

## 4. Give your AI tools access

Changing access needs the GBrain server stopped for a minute.

1. Stop the server:
   ```bash
   launchctl bootout gui/$(id -u)/com.gbrain.serve
   ```
2. List your AI tools and what each can read:
   ```bash
   gbrain auth clients
   ```
   Each entry shows a name (for example `opencode`), a client id (`gbrain_cl_…`) and
   `federated reads`.
3. For each tool that should search your documents, add `docs` to its reads:
   ```bash
   gbrain auth rescope-client <client id> --federated-read default,projects,docs
   ```
   Use that tool's own `federated reads` list from step 2 and add `docs` at the end. The list
   **replaces** the old one, so a source you leave out is no longer readable.
4. Start the server again:
   ```bash
   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.gbrain.serve.plist
   ```

Your AI tools pick up the new access on their next request; no reinstall needed.

## 5. Sync again and test

Run the sync from step 2 again. Then ask your AI tool a question that only one of your documents
can answer, for example *"What does the ACME Bank RFP say about single sign-on?"*. The answer
should point to a file under `docs-mirror/`.

## You'll see

```text
Converted 0 · unchanged 92 · removed 0 · skipped 7
GBrain updated
```

On later syncs, *GBrain already up to date* when nothing changed.

## Keep it current

Add the sync to your nightly job, after the GBrain server is running. Guard it so it runs only
when both settings are on:

```bash
SFAL="$HOME/.sf-activity-log/bin/sfal"
if "$SFAL" docs status | python3 -c 'import json,sys; s=json.load(sys.stdin); sys.exit(0 if s["enabled"] and s["gbrain_import"] else 1)'; then
  "$SFAL" docs sync
fi
```

## When to do it again

| Change | Register again? | Give access again? |
|---|---|---|
| Add an account to `docs_mirror.accounts` | No | No |
| Connect a new AI tool to GBrain | No | Yes, for that tool: include `docs` in its reads |
| Move the mirror (`docs_mirror.output`) | Yes, remove `docs` and add it with the new path | No |
| Set up on a new Mac | Yes | Yes |

## If something goes wrong

| Message | What to do |
|---|---|
| `not_a_git_repo` when registering | Do step 2 first. Do not use `--force`: GBrain could not update a plain folder |
| Sync says *storage_error* or *GBrain failed* | The source is not registered yet: do step 3. The copies are fine; the next sync tries again |
| An AI tool says *not granted docs* or finds nothing | That tool has no access: do step 4 for it |
| `pglite_busy` during step 4 | The server is still running: do step 4.1 first |
| *GBrain isn't installed* | Set `gbrain_import: false`, or install GBrain |

## Undo it

```bash
gbrain sources remove docs --confirm-destructive
```

This removes the copies from GBrain only. Then set `gbrain_import: false`. Your mirror folder and
original documents stay as they are.

Next: [Search your documents](search-your-documents.md) · [Configuration](../reference/configuration.md#docs-mirror)
