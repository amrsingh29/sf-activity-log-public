# How it works

> The daily-to-weekly loop, the six steps of a weekly run, and one meeting followed end to end.

## The loop

```
during the week                         end of the week
───────────────                         ───────────────
meeting, call, deck                     calendar + email + notes + files
      │                                               │
Capture a note  ──► activity note ───────────────►  Log your week ──► you approve ──► Excel
(/log-activity-note)  (your record,                  (/sf-log)          (review)       (paste into
                       per customer)                                                    Salesforce)
```

Notes are optional but make the weekly run better: they carry what happened, the account and
the hours, so it asks fewer questions.

## A weekly run, step by step

Only two steps involve the AI; the rest are fixed rules in the engine.

```
1 prepare   engine   read sources → drop noise → match accounts → skip what is already logged
2 propose   AI       group evidence into records → type → notes → mark unknowns [to confirm]
3 validate  engine   21 logging guide checks; AI fixes until clean
4 review    you      answer questions, change anything, approve
5 commit    engine   append to the ledger (needs the approval code)
6 render    engine   Excel + Markdown for the period
```

## Example: one meeting, end to end

**Evidence.** Your calendar has *"ACME - incident summarisation demo"*, Tue 6 Oct 10:00–11:30,
with two `@acme.com` attendees. The day before you sent *"Demo agenda"* to `acme.com`.

**1 · Prepare.** The engine finds both items, matches `acme.com` to **ACME Bank** in your
account list, and sees nothing logged yet:

```
cal:3f2a…  Tue 06 Oct 10:00  1.5h  ACME - incident summarisation demo   ACME Bank (domain)  demo_title
mail:9c1d… Mon 05 Oct          -   Demo agenda                          ACME Bank (domain)  sent_by_me
```

**2 · Propose.** The AI makes one record from both items:

| Account | Type | Date | Hours | Prep | Notes |
|---|---|---|---|---|---|
| ACME Bank | 07 · Product Demo | 2026-10-06 | 1.5 | `[to confirm]` | Demonstrated incident summarisation to the ACME ITSM team; agenda sent 5 Oct. |

**3 · Validate.** The engine checks, among others: 1.5h does not exceed the 1.5h meeting (C04),
the date matches the evidence (C13), the account is in your list (C05), there is a
no-opportunity reason (C06). It passes and returns an **approval code**.

**4 · Review.** You are asked about prep time; you answer `30m`. The record becomes
`Prep Hours 0.5`, citing `user:30m prep`. You say *approve*.

**5 · Commit.** The engine re-checks the proposal, confirms the approval code matches what you
reviewed, and appends record `A0021` to the ledger.

**6 · Render.** `output/2026/weeks/2026-W41_…/Salesforce_Activity_Log_….xlsx` now has the row on
**Paste-Ready**, and the **Evidence Trail** sheet links it to both the meeting and the email.

## Why it is built this way

- **Exact things are code.** Reading sources, hours limits, the logging guide rules and writing
  files give the same result every time, whichever AI you use.
- **Judgment is AI.** Grouping evidence, choosing the type and writing notes need language.
- **You approve.** The approval code ties the commit to exactly what you saw.

More: [AI and engine](ai-and-engine.md) · [Safety](safety.md) · [Sources](../reference/sources.md)
