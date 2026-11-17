# Note format

> The structure of an activity note - what `/log-activity-note` writes and what the weekly log
> reads. You can also write notes by hand in this format.

## File

| Item | Value |
|---|---|
| Name | `YYYY-MM-DD_HHMM_<topic>_activity-note.md` (central: `…_<account>_<topic>_activity-note.md`) |
| Where | `<log folder>/notes/YYYY/MM/` (central) or `<customer folder>/_ActivityLogging/` |
| Same name exists | `-2`, `-3` is added - notes are never overwritten |

## Header (read by the weekly log)

| Field | Meaning |
|---|---|
| `type` | `activity-note` |
| `note-id` | the note's permanent id - it stays the same when you move or rename the file or its folder; do not edit or copy it |
| `title` | short, specific title |
| `account` | Salesforce account - trusted over any guess from the folder |
| `activity-date` | day of the activity (`YYYY-MM-DD`) - not necessarily the day the note was written |
| `duration-hours` | total hours, only when every activity's hours are known |
| `evidence` | ids of the meetings, emails or files it is based on |
| `created`, `source` | when and by what it was written |

## Body

| Section | Content |
|---|---|
| fields line | `**Account:** … · **Activity date:** … · **Duration:** …` (`[to confirm]` when unknown) |
| `## Summary` | 1-3 sentences |
| `## <activity title>` | one per activity: time and hours, *what*, **Context**, **Discussed**, **Outcomes & decisions**, **Next steps**, **People** table |
| `## Follow-ups` | checklist `- [ ] …` |
| `## Background` | cited GBrain context: `` - `page/slug` - text `` |
| `## To confirm` | anything that could not be verified |

Sections with nothing to say are left out.

## Example

```markdown
---
type: activity-note
note-id: 3f9c2a71e8b04d55
title: ACME Bank - on-prem right-sizing (PSR guidance)
account: ACME Bank
activity-date: '2026-10-14'
duration-hours: 0.5
evidence: [cal:5c4bfbda9adb, mail:d8bb958733fc]
---
# ACME Bank - on-prem right-sizing (PSR guidance)

**Account:** ACME Bank · **Activity date:** Wed 14-Oct-2026 · **Duration:** 0.5 h

## Summary
Sync with the PSR team on sizing for ACME's production deployment and growth.

## Right-sizing sync with PSR
*Wed 14 Oct · 0.5 h*

**Context**
- Per the invite email: growth in knowledge articles, user adoption, more AI agents

**Outcomes & decisions**
- A bigger-team call will be set up for Thu 15 Oct

**People**
| Person | Role / status |
|---|---|
| Patel, Nina | PSR - accepted |

## Follow-ups
- [ ] Run the bigger-team right-sizing call (15 Oct)

## Background
- `singapore/acme/account-plan` - POC phase 1 runs in parallel

## To confirm
- Exact meeting time
```

## Hours rules

| Hours shown as | When |
|---|---|
| `0.5 h` | taken from the matching meeting |
| `1 h (you said: "about an hour")` | stated by you, with your words |
| `[to confirm]` | anything else |

Older notes written by hand or by earlier tools (`**Activity:**`, `**Duration:**` lines, a date
in the title) are read too - see [Sources](sources.md#notes).
