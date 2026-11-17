---
name: sf-docs
description: Docs mirror workflow. Run ONLY when explicitly invoked - the /sf-docs-sync or /sf-docs-status command or recipe.
---

# Docs mirror

Make the user's customer documents (Word, PowerPoint, PDF and some Excel files) searchable by
converting them into text copies. The engine does all of it: which files, which account, what
changed, what is skipped. You only run it and explain the result in plain words.

## Tools
Use the MCP tools if you have them, else the CLI `~/.sf-activity-log/bin/sfal`:

| Step | MCP | CLI |
|---|---|---|
| sync | `sfal_docs_sync(account?, dry_run?, rebuild?)` | `sfal docs sync [--account <name>] [--dry-run] [--rebuild]` |
| status | `sfal_docs_status()` | `sfal docs status` |

## /sf-docs-sync
1. Read the user's words: an account name → `account`; "dry run", "preview" or "what would" →
   `dry_run`; "rebuild" or "from scratch" → `rebuild`. Nothing given → all selected accounts.
2. Run sync once. If it returns `ok: false`, show the `error` and what to fix (most often:
   `docs_mirror.enabled` is false or no accounts are chosen in the profile). Show the exact
   lines to add to `~/.sf-activity-log/profile.yaml` and stop. Do not offer to add them, and do
   not edit the profile even if the user asks: say "Please add these lines yourself; I don't
   change your profile."
3. Report in at most 8 short lines, numbers exactly as returned:
   - one line of counts: converted, unchanged, removed, skipped;
   - skipped by reason, one line each (count only; list files only if the user asks);
   - every `warning`, word for word, first;
   - `low_text` files as "probably scanned, no text found";
   - `errors`, if any.
4. GBrain: if `gbrain` is present, add one line: `updated` → "GBrain updated"; `up_to_date` →
   "GBrain already up to date"; `skipped` → its `reason`; `failed` → its `reason`, then its `fix`
   word for word, and say the copies are fine and the next sync tries again. Do not run the fix.
   If `next` is present instead, show it as one line. If neither is present, say nothing about
   GBrain at all.
5. A dry run changes nothing: say so.
6. End with this line, filling in a real account name from the result (or the profile):
   `Options: /sf-docs-sync <account> · /sf-docs-sync dry run · /sf-docs-sync <account> dry run · /sf-docs-sync rebuild · /sf-docs-status`
   (In Goose and Open Worker drop the leading slash.)

## /sf-docs-status
Run status and report: last run, copies per account, mirror size, whether GBrain updates are on
(`gbrain_import`, `gbrain_last_ok`), and the skipped lines from the last report. If `enabled` is false, say the mirror is off and which setting turns it on.
End with the same `Options:` line as /sf-docs-sync.

## Rules
- Never edit, write or offer to edit the profile file. Only the user changes it.
- Never convert, copy or open documents yourself; only the engine does that.
- Never suggest ways around a protected file. "Protected" means it stays out.
- Unassigned files match no account in the profile: suggest adding an alias with
  /sf-add-customer only if the user asks how to include them.
