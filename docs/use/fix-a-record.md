# Fix a record

> Correct, remove or add a record after it was logged. History is kept: the old record is
> voided and a corrected one added.

**Before you start:** your profile is set up and the record is in the ledger.

## Change a record (wrong hours, type, account…)

Ask in plain words during any run, for example:

```
A0003 was 5 hours, not 4.
```

The AI proposes two changes - void `A0003`, add a new record with 5 hours - validates them and
shows the review table. Approve, and the Excel file for that period is rebuilt:

- the old version moves to the period's `history/` folder,
- the **Per-Customer Deltas** sheet shows `A0003 replaced by A0013, +1h`.

Then update the record in Salesforce.

## Remove a record

```
Remove A0007, I did not attend.
```

The record is voided (kept in the ledger with `voided = true`) and drops out of every output.

## Add something that was missed

```
Add a 1h call with ACME Bank on 8 Oct about the RFP pricing questions.
```

Hours you state are recorded as *user-confirmed* evidence.

## Long-running records (Value Review, POC/POV, RFP)

These stay **one record per engagement**. New sessions **extend** it: hours accrue and the
Activity Date moves to the latest session. The AI does this automatically when it finds an
open record; in Salesforce, update the existing activity's hours rather than creating a new one.

## Find a record

```
What did I log for ACME Bank in September?
```

The AI reads the ledger and answers with record IDs (A0001…).

Next: [Re-run a period](rerun-a-period.md)
