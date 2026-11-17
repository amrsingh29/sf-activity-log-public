# Security and safety

## What the tool guarantees

- **Nothing is logged without your approval** - an approval code ties the commit to the exact
  proposal you reviewed.
- **Nothing is invented** - anything not backed by evidence stays `[to confirm]`.
- **History is never lost** - the ledger is append-only; corrections void and supersede.
- **It only writes where it should** - your log folder, Downloads (if enabled) and, for notes,
  the folder you chose.
- **Your data stays with the company AI** - Cortex only, and only what each job needs; never file
  contents, never your whole mailbox. Exception: in Claude Code the same text goes to Anthropic
  instead - check your company's policy first.

How each guarantee is enforced: [Safety](docs/understand/safety.md).

## Keys and personal files

- The Cortex API key lives in the macOS Keychain, never in a file in this repository.
- Your profile (`~/.sf-activity-log/profile.yaml`) and log folder stay on your Mac or your
  OneDrive, and are never committed.

## Reporting a problem

Found a way it could log without approval, lose history or leak something? Do not open a public
issue with the details - contact the repository owner directly. Remove customer names and email
content from any report.
