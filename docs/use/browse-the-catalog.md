# Browse your catalog

> See every activity note, Salesforce record and logged week in one searchable page - grouped by
> customer, with what is not logged yet.

**Before you start:** at least one note saved or one week logged. The catalog is a page in your
log folder: `<your log folder>/catalog/index-modern.html`.

## 1. Open it

| Tool | Open it |
|---|---|
| Any tool, or Finder | In Finder, open your log folder → `catalog` → `index-modern.html`. Bookmark it in your browser. |
| Terminal | `~/.sf-activity-log/bin/sfal catalog --open` |

It updates itself every time you save a note, approve a week or build the Excel file - you never
need to rebuild it. To rebuild by hand: `~/.sf-activity-log/bin/sfal catalog`.

## 2. Find what you need

| Tab | Shows |
|---|---|
| **Notes** | Every activity note - in customer folders and in the central folder. Click one to read it in full, see its follow-ups and open the file. |
| **Records** | Every Salesforce record: date, account, type, hours, status (ready, held - to confirm, voided). Click a column header to sort (again to reverse); click a row for its details and the notes behind it. |
| **Calendar** | A month view: each day shows its notes and records, with the day's hours; a Week column totals hours, records and notes. Click a day for its list, an item to open it; ‹ › to change month. On a phone it becomes a day-by-day list. |
| **Periods** | Every logged day, week or month, with totals and links to its Excel and Markdown files. |
| **Accounts** | One card per customer: hours, notes, records and open follow-ups. Click for the full timeline. |

Search covers titles, summaries, the full note text and follow-ups. Filter by account and time.
Each tab has one extra filter: notes **not logged yet** (also on the calendar), **voided** records,
periods with **held** records, accounts with **open follow-ups**.

**You'll see:** a green *logged A0042* on notes behind a record, an orange *not logged yet* on the
rest, and *held - to confirm* on records missing a fact.

## Good to know

- The page is **read-only**. To change something, use your AI tool ([Fix a record](fix-a-record.md),
  [Capture a note](capture-a-note.md)).
- It lives in your log folder, next to the ledger, because it shows customer content. It needs no
  internet and no AI.

Next: [Log your week](log-your-week.md) · [Capture a note](capture-a-note.md)
