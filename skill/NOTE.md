---
name: log-activity-note
description: Log Activity Note workflow. Run ONLY when explicitly invoked - the /log-activity-note command or the Log Activity Note recipe.
---

# Log Activity Note

Turn what the user did into **detailed, well-structured activity notes**, one per customer,
while it is fresh. The notes are a record worth reading later and the evidence for the weekly
SF Activity Log run. Quality matters more than speed - but ask few questions.

## Tools
Use the MCP tools if you have them, else the CLI `~/.sf-activity-log/bin/sfal`:

| Step | MCP | CLI |
|---|---|---|
| 1 context | `sfal_note_context(day)` | `sfal note-context [day]` |
| 2 detail | `sfal_note_detail(ids, day)` | `sfal note-detail <id> [<id>…] --day <day>` |
| 3 where | `sfal_note_targets(account)` | `sfal note-targets <account>` |
| 4 save | `sfal_note_save(note, target)` | note JSON to a temp file → `sfal note-save --file <f> --target <t>` |
| background (if `gbrain` is true and you have GBrain tools) | GBrain `search` / `query` / `get_page` | same |

## Rules
1. **Expand, never invent.** Build the note from the user's words + the detail you fetched.
   Never invent people, titles, numbers, decisions, dates or hours. Anything missing that matters
   → write it as `[to confirm]` and list it under `to_confirm`.
2. **Use the real evidence.** Always fetch detail (step 2) for the items a note is about - invite
   descriptions and email bodies carry the agenda, concerns and decisions. Quote their substance
   ("per the invite: …", "per the email to the PSR team: …").
3. **Identify the right activity.** If the user's words and the evidence disagree (e.g. they say
   "weekly sync" but the evidence is a different meeting or email thread), say so and ask.
4. **Hours** come only from the matched meeting (`hours`), or from the user - then set
   `hours_source: "user"` and `hours_quote` to their exact words ("about an hour"); the note shows
   them. Otherwise `"[to confirm]"`. Never mark hours as user-stated unless the user said them.
   The engine rejects anything else.
5. **One activity, one thing.** Do not merge separate activities (e.g. a weekly sync and a
   separate email thread about another topic) into one. If an activity resembles a calendar
   meeting of that day, cite that meeting; if it is a different activity, confirm with the user
   and list the meeting id in `not_meetings`. The engine refuses a likely mix-up.
6. **Paths** are never yours to choose - only `central` or a `target` from step 3.
7. **Few questions** (at most 3 per batch), plain text, short messages. Save only after the
   user confirms ("y", "ok", Enter).

## Flow
1. **Context.** `note_context(day)` - default today; the user may say "yesterday" or a date.
   - The user typed activities (one or a list) → match each to context items.
   - The user typed nothing → show the day's items as a short numbered list and ask which to note
     (several allowed) and anything to add.
2. **Detail.** `note_detail(ids)` for every matched item. Read descriptions, attendee statuses and
   email bodies.
3. **Group by customer** - one note per account per batch (internal work → the internal account).
   Several activities for one customer = several activity sections in one note.
4. **Background (optional).** If `gbrain` is true and GBrain tools exist: look up the account
   (account plan, recent meeting notes) and add 1-4 cited lines that help read this activity
   (`source` = page slug). If nothing useful comes back, skip silently.
5. **Where.** `note_targets(account)` → use `recommended`; if null ask the user to pick from `options`.
6. **Confirm.** Show each note compactly and ask once for the batch:
   ```
   1) ACME Bank · Wed 14 Oct · 0.5 h → Singapore/ACME Bank/_ActivityLogging/
      ACME Bank - HelixGPT on-prem right-sizing (PSR guidance)
      Activities: Right-sizing sync with Nina Patel (PSR)
      Follow-ups: schedule bigger-team call (15 Oct) · To confirm: meeting time
   Save all? (y / edit 1 / skip 1)
   ```
7. **Save** each note; reply with the saved paths, one per line.

## Note structure (for note_save)
```json
{"title": "ACME Bank - HelixGPT on-prem right-sizing (PSR guidance)",
 "topic": "helixgpt right-sizing psr sync",
 "account": "ACME Bank", "activity_date": "2026-10-14",
 "summary": "Organised a sync with the PSR team (Nina Patel) to get sizing guidance for ACME's HelixGPT on-prem production deployment and future growth.",
 "activities": [{
   "title": "Right-sizing sync with PSR (Nina Patel)",
   "time": "Wed 14 Oct", "duration_hours": "[to confirm]",
   "what": "Sought PSR guidance on sizing considerations, field observations and best practices for ACME's production deployment and growth.",
   "context": ["Per the invite email: ACME Bank worries about growth in knowledge articles, user adoption, more AI agents, long-term scalability"],
   "discussed": ["CPU / memory sizing", "Storage (PVC / database)", "Scalability headroom"],
   "outcomes": ["A bigger-team call will be set up for Thu 15 Oct"],
   "next_steps": ["Shared the invite for 15 Oct with the PSR team"],
   "people": [{"name": "Patel, Nina", "role": "PSR - accepted"}, {"name": "Wong, Leo", "status": "declined"}],
   "evidence": ["mail:07c81837140b"]}],
 "follow_ups": ["Run the bigger-team right-sizing call (15 Oct)"],
 "background": [{"text": "HelixGPT POC Phase 1 runs in parallel; this sizing supports the production deployment.", "source": "singapore/acme/account-plan"}],
 "to_confirm": ["Exact meeting time and duration"]}
```
Only `title`, `account`, `activity_date`, `summary` and at least one activity with `title` and
`what` are required. Leave out sections you have nothing for - never pad them.
