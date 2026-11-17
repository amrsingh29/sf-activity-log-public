# Search your documents

> Make your Word, PowerPoint and PDF files searchable by your AI tools, account by account.
> Your folders are only read; text copies go to a separate local folder.

## Before you start

- Your profile has `workspace.root` and your accounts ([Update your profile](update-your-profile.md)).
- Decide which accounts to include. Leave out any customer whose documents must not be copied,
  even on your own laptop.

## 1. Turn it on

Add this to `~/.sf-activity-log/profile.yaml`, with your own account names:

```yaml
docs_mirror:
  enabled: true
  accounts: [ACME Bank, Globex]      # or [all] with exclude_accounts: [Initech]
```

Every other setting has a sensible default ([Configuration](../reference/configuration.md#docs-mirror)).

## 2. Preview it

| Tool | Type this |
|---|---|
| Goose Desktop | Recipes → **SF Activity Log - Sync Documents**, type *dry run* |
| Goose CLI | `goose run --recipe sf-docs-sync -s`, then *dry run* |
| OpenCode, Claude Code, omp, Hermes | `/sf-docs-sync dry run` |
| Open Worker | ask *"sf-docs-sync dry run"* |

A dry run writes nothing. It shows how many files would be converted and why others are skipped.

## 3. Sync

Run the same command without *dry run*, or for one account: `/sf-docs-sync ACME Bank`.
The first run takes a few minutes; after that only changed files are converted.

## 4. Make it searchable in GBrain (optional)

If you use GBrain, set `docs_mirror.gbrain_import: true` and follow
[Search your documents in GBrain](search-documents-in-gbrain.md) once. After that every sync
updates GBrain by itself.

To keep the mirror current without typing, add `~/.sf-activity-log/bin/sfal docs sync` to your
nightly job.

## You'll see

```text
Converted 92 · unchanged 0 · removed 0 · skipped 14
  larger than 20 MB: 2 · excel name not matched: 5 · protected: 7
```

Copies are organised by account, whatever your folder layout:

```text
~/.sf-activity-log/docs-mirror/ACME Bank/2026/RFP-Pack.pdf.md
```

Each copy starts with the path of the original, so answers can point you to the real file.

## Good to know

- **Protected files stay out**: encrypted or rights-managed files, password PDFs, PDFs that do not allow copying.
- **Online-only files are not downloaded.** To include a folder, set it to *Always keep on this device*.
- **Files that match no account** are not copied; with `accounts: [all]` they are counted in the report. Add an alias with `/sf-add-customer`.
- **Deleted, renamed or deselected files** lose their copy on the next sync.
- **The git repo stays on your Mac.** It has no remote and is never pushed.
- Status at any time: `/sf-docs-status`.

Next: [Commands](../reference/commands.md)
