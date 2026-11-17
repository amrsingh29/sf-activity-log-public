# Use Copilot, Word or Excel exports

> Use a Copilot summary or a Word, Excel or CSV export as evidence - when the tool cannot read
> your calendar or mail, or you have activities listed elsewhere.

## 1. Turn on imports

In your profile ([how](update-your-profile.md)):

```yaml
sources:
  imports:
    enabled: true
```

## 2. Drop the file in the inbox

Put it in `<your log folder>/inbox/`, for example
`~/OneDrive/Customers/_SFActivityLog/inbox/copilot-week41.docx`.

Supported: `.docx`, `.xlsx`, `.csv`, `.txt`, `.md`.

## 3. Run the period as usual

The file is read on every run; only items dated inside the period are used.

## What gets picked up

**Tables** - columns are recognised by name:

| Recognised headers | Used as |
|---|---|
| Date, Day, Meeting Date, Start Date | date |
| Time, Start Time, Start | time (e.g. `10:00-11:30`) |
| Duration, Hours, Length | hours (`1h`, `90 min`) |
| Subject, Meeting, Title, Topic | title |
| Organizer, From | people |
| Account, Customer, Client | account hint |

**Text** - any line containing a date in the period becomes an item, quoting that line.

## Good to know

- Imported items are marked **partial**: Copilot summaries often miss meetings. If the document
  says "25 meetings" but fewer are found, you get a warning.
- A meeting that is also in your calendar is merged - the calendar's exact times win.
- Ask Copilot for a table with Date, Time, Subject, Organizer, Customer columns, one week at a
  time - it parses best.

Next: [Sources reference](../reference/sources.md)
