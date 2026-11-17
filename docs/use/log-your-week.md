# Log your week

> Turn the week's calendar, email, notes and files into Salesforce records, approve them, and
> paste from the Excel file. About 5 minutes once your profile is set up.

**Before you start:** your profile is set up. Capturing notes during the week
([Capture a note](capture-a-note.md)) means fewer questions now.

## Steps

1. Run it on Friday or Monday:

   | Tool | Type this |
   |---|---|
   | Goose Desktop | Recipes → **SF Activity Log** → ▶, period `last week` |
   | Goose CLI | `goose run --recipe sf-log --params period="last week" -s` |
   | OpenCode, Claude Code, omp, Hermes | `/sf-log last week` |
   | Open Worker | ask *"sf-log last week"* |

   Use `this week` on a Friday afternoon. Other periods: [Commands](../reference/commands.md#periods).
2. Read the **source summary**. A failed source or a warning means missing activities - decide
   whether to continue.
3. Answer the **questions** (below).
4. Check the **review table**. Change anything in plain words: *"row 2 is 04 Technical
   Presentations"*, *"add 1 hour prep to row 1"*, *"drop row 5"*.
5. Type **approve**. Nothing is written before this.
6. Open the Excel file (Downloads) → **Paste-Ready** → paste into Salesforce. Columns follow the
   Salesforce form, left to right.

**You'll see:** `Salesforce_Activity_Log_<from>_to_<to>.xlsx` in Downloads and in your log
folder ([Output](../reference/output.md)).

## Answering questions

Only items it cannot decide become questions, each with a default:

| Reason shown | Default |
|---|---|
| declined by email / not on the invite / broadcast (many invited) | Skip |
| overlaps another meeting / RSVP tentative / no RSVP | Log if customer, else Skip |
| email only, hours unknown / hours not stated | ask for hours (customer) or Skip |
| file work, nothing logged | Skip |

| Goose | OpenCode | Other tools |
|---|---|---|
| a prompt per item: Enter = default, `l` log, `s` skip, or a time (`45m`, `1.5h`) | tabs with arrow keys, or type your own | a list - reply `ok` or `1 log, 3 hours 45m` |

A time that looks wrong (e.g. `20` for a 45-minute meeting) is asked back: minutes or hours?

## Month end

Run it with period `last month` to catch late evidence and get a monthly total. Nothing is
logged twice - already-logged items are skipped.

Next: [Fix a record](fix-a-record.md) · [Re-run a period](rerun-a-period.md)
