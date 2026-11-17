# Capture a note

> Record what you just did - a meeting, a call, a deck - as a detailed note while it is fresh.
> A minute or two. The weekly log reads these notes, so nothing is forgotten.

**Before you start:** your profile is set up ([Start here](../README.md#start-here)).

## Steps

1. Run it:

   | Tool | Type this |
   |---|---|
   | Goose Desktop | Recipes → **Log Activity Note** → ▶ |
   | Goose CLI | `goose run --recipe log-activity-note --params what="…" -s` |
   | OpenCode, Claude Code, omp, Hermes | `/log-activity-note …` |
   | Open Worker | ask *"log activity note: …"* |

2. Say what you did - one activity or a list, in your own words:
   *"ACME sizing sync with PSR, pricing due Friday; Globex deck for Thursday"*.
   Leave it empty to pick from the day's meetings, mail and files.
   Another day? *"note yesterday's call with Globex"*.
3. Answer its questions - at most a few, usually which customer or how long.
4. Check the notes it shows and say **y** (or tell it what to change).

**You'll see:** one note per customer, saved where your profile says, and the file path:

```
1) ACME Bank · Wed 14 Oct · 0.5 h → Singapore/ACME Bank/_ActivityLogging/
   ACME Bank - on-prem right-sizing (PSR guidance)
   Follow-ups: run the bigger-team call (15 Oct) · To confirm: exact time
Save all? (y / edit 1 / skip 1)
```

## What goes into a note

It reads the full detail of the matched items - invite descriptions, who accepted or declined,
the emails you sent - and, with GBrain on, adds cited background. Each note has a summary; per
activity what, context, discussed, outcomes, next steps and people; follow-ups; and a
**To confirm** list for anything it could not verify. [Note format](../reference/note-format.md)

It never invents names, numbers or hours:

- Hours come from the matching meeting, or from you - then your words are shown
  (*"1 h (you said: 'about an hour')"*). Otherwise `[to confirm]`.
- If your words point to a different meeting than the evidence (e.g. "weekly sync" vs a separate
  email thread), it asks instead of merging them.

## Where notes are saved

| Setting `sources.notes.save_to` | Saved to |
|---|---|
| `central` (default) | `<log folder>/notes/2026/10/…_activity-note.md` |
| `customer_folder` | `<customer folder>/_ActivityLogging/…_activity-note.md` |

In customer-folder mode the folder comes from your account list (name or alias in the folder
name, also customers nested under a partner folder). The AI never chooses a path. Several matches
→ it asks; none → saved centrally and it tells you. Notes are never overwritten.

Next: [Log your week](log-your-week.md)
