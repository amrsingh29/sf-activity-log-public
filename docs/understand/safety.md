# Safety

What the tool guarantees, and how.

## Nothing is logged without your approval

`validate` returns an **approval code** - a fingerprint of the exact proposal you were shown.
`commit` re-validates and refuses if the code does not match. If anything changes after you
reviewed it, it must be validated and shown again.

## Nothing is invented

- Every record must cite evidence (check C12); its date must match the evidence (C13).
- Hours cannot exceed the evidence (C04) unless you stated them - then they are recorded as
  `user:<your words>`.
- Anything unknown is `[to confirm]` and the record is **held** out of Paste-Ready.

## History is never lost

- The ledger only grows. Corrections void the old row and add a new one.
- Every ledger action is in `ledger/audit.log`.
- Each period keeps earlier Excel versions in `history/`; `runs.md` lists every build.
- Each run's evidence is kept in `cache/<run_id>/`.

## It only writes where it should

| Location | Access |
|---|---|
| Calendar, Mail, customer folders | **read only** (except activity notes, below) |
| `data_dir` (your log folder) | write - ledger, outputs, notes, and the catalog page |
| `mirror_to` (e.g. Downloads) | write - copy of the latest Excel file |
| `docs_mirror.output` (only when the docs mirror is on) | write - text copies of documents; never inside OneDrive or your folders. With `gbrain_import`, also a local git repo there (no remote) and a `gbrain sync` of it |
| `~/.sf-activity-log/profile.yaml` | written only by setup, after you confirm, with a backup |
| `_ActivityLogging/` in a customer folder | activity notes only, and only in a folder matched to the note's account; never overwrites |

Any other write is refused by the engine.

## Your data stays with the company AI

The AI sees what each job needs, and only through the company-approved AI (Cortex):

| Job | The AI sees |
|---|---|
| Log your week | meeting titles, attendee names and domains, email subjects and short previews, note summaries, file names and Office document titles |
| Capture a note | the above for the day, plus - for the items you choose to note - invite descriptions, attendees' responses and the full text of those emails |

It never sees file contents, and never your whole mailbox.

**Exception - Claude Code.** If you run the commands in Claude Code, the same text goes to
Anthropic instead of Cortex. Check your company's policy before using it with customer data.

## Least privilege in Goose

The Goose recipes load only the `sfal` tools - no shell and no general file access.

## The rules are the same for everyone

The logging guide rules are a shared, versioned rule pack ([Rules](../reference/rules.md)).
Every record stores the rule-pack version it was checked against.
