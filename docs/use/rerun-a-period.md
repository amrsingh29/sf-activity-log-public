# Re-run a period

> Run a past week, month or range again - for example after a late note or a missed meeting.
> Nothing is logged twice.
Run the **SF Activity Log** recipe with the period, e.g. `2026-10-05 to 2026-10-11`
(Goose terminal: `goose run --recipe sf-log --params period="2026-10-05 to 2026-10-11" -s`).

## What happens

- Evidence already logged is listed as **already logged** - it is never logged twice.
- Only new evidence becomes questions or proposals.
- After you approve, the period's Excel file is rebuilt.

## Where the files go

The folder depends only on the dates - the same week always lands in the same place:

| You ask for | Folder |
|---|---|
| `today`, `2026-10-14` | `output/2026/days/2026-10-14/` |
| `last week`, `2026-10-05 to 2026-10-11` (Mon–Sun) | `output/2026/weeks/2026-W41_2026-10-05_to_2026-10-11/` |
| `October`, `last month` | `output/2026/months/2026-10_October/` |
| any other range | `output/2026/ranges/<from>_to_<to>/` |

## Versions

| Situation | Result |
|---|---|
| Nothing changed | files overwritten in place |
| Something changed | previous version moved to `history/`, **Per-Customer Deltas** sheet shows what changed |

`runs.md` in each folder lists every rebuild with what changed.

## Day, week and month together

A day, its week and its month are all views of **one ledger**. Running each of them never
double-logs; the month file always shows the full month.

Next: [Output reference](../reference/output.md)
