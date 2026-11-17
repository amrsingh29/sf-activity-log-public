# Sources reference

What each evidence source reads, what it filters out, and what it can prove.
Turn sources on or off in your profile ([configuration](configuration.md)).

| Source | Reads | Proves an activity? | Gives hours? |
|---|---|---|---|
| calendar | macOS Calendar (your Exchange account) | yes - main source | yes, exact duration |
| email | macOS Mail, only the mailboxes you list | yes - work with no meeting | no (asked) |
| notes | your Markdown activity notes | yes | only if the note states them |
| imports | files in `<log folder>/inbox/` | yes (partial) | only if stated |
| files | your customer folder | only as *possible unlogged work* | no |
| gbrain | knowledge base (optional) | no - wording context only | no |

## Calendar

Reads every event in the period; recurring meetings are expanded.

| Dropped automatically | Flagged for a question |
|---|---|
| cancelled ("Canceled: …") | broadcast (more than `broadcast_threshold` invitees) |
| declined by you | no RSVP / tentative |
| all-day events, holidays | overlaps another meeting |
| titles in `ignore_titles` | not on the invite |

Your RSVP emails ("Accepted: …", "Declined: …") confirm or contradict attendance for the
matching occurrence.

## Email

- Only the mailboxes in `sources.email.mailboxes` (default `Sent Items`).
- Messages of one thread on one day become one item.
- Dropped: no-reply senders, auto-replies, mail to more than 25 people, `ignore_subjects`.
- Reads subject, people's domains, attachment names and a 300-character preview for the weekly
  log. Capture a note reads the full text of the emails you are noting (quoted history and
  signatures removed).

## Notes

Read from two places: the central notes folder (`<log folder>/notes/`) and, when you have a
customer folder, `**/_ActivityLogging/*.md` inside it. Write them with
[Log activity notes](../use/capture-a-note.md) or by hand.

One Markdown file = one item. The **account** comes from the note's `account:` header when present
(trusted over any guess), else from its folder. The **activity date** is taken from, in order:
frontmatter `activity-date`, an `Activity date:` line, a date in the title, the note's own date.
Hours come from a `Duration:` or `Hours:` line.

```markdown
---
title: ACME Bank - RFP clarification call (07-Oct-2026)
---
**Activity date:** 07-Oct-2026 · **Duration:** 1.5 h
## Summary
Walked the ACME procurement team through the ITSM response…
```

## Imports

See [Use exports](../use/use-exports.md). Items are marked partial; meetings already in the
calendar are merged.

## Files

Files created or changed in the period, in your customer folder:

| Signal | How it is decided |
|---|---|
| authored by you | Office "last modified by" is you |
| received | downloaded (Spotlight "where from") |
| sync burst (dropped) | many files across accounts in the same minute |

Files are grouped per account per day. A group near a known activity of the same account is
its **prep / follow-up**; otherwise it is **possible unlogged work** - a question, never a
record by itself.

## Accounts

Every item is matched against your account list using its title, folder path, file names and
email domains. Partner + customer in the same item → the customer. No match or two customers →
`[to confirm]`.
