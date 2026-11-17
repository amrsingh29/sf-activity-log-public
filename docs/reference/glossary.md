# Glossary

| Term | Meaning |
|---|---|
| **Activity note** | Your detailed record of one or more activities for one customer, written with Capture a note ([format](note-format.md)) |
| **Account registry** | The list of customers and partners in your profile, used to match evidence to Salesforce accounts |
| **Already logged** | Evidence that is already behind a record in the ledger; it is never logged again |
| **Approval code** | Short code from the latest validation; a commit is refused without it, so nothing changes after you review |
| **Broadcast** | A call with many invitees (default more than 40) - asked, not assumed |
| **Commit** | Writing approved records to the ledger |
| **Consolidated record** | One record per Value Review, POC/POV or RFP; later sessions extend it |
| **Data folder / log folder** | `data_dir` - where the ledger, outputs, cache and inbox live |
| **Decision** | An item the engine cannot decide (declined, broadcast, email-only…), asked with a default |
| **Engine** | The program that reads sources, applies the rules and writes files - no AI inside |
| **Evidence** | A calendar event, email thread, note, file group or imported line that supports a record |
| **Extend** | Add a new session's hours to an open Value Review/POC/RFP record |
| **Held** | A valid record with something `[to confirm]`; kept in the ledger, left out of Paste-Ready |
| **Host** | The AI tool you run it in - Goose, OpenCode, Claude Code, Open Worker, omp or Hermes |
| **Ledger** | `ledger.csv`, the single source of truth |
| **Paste-Ready** | The Excel sheet with ready records in Salesforce form order |
| **Period** | The date range of a run - a day, week, month or custom range |
| **Possible unlogged work** | File activity with no matching record - asked, never logged automatically |
| **Profile** | `~/.sf-activity-log/profile.yaml`, your personal settings |
| **Rule pack** | The logging guide rules in machine form, shared by everyone ([Rules](rules.md)) |
| **Run** | One `prepare` → review → commit cycle; its evidence is kept in `cache/<run_id>/` |
| **Sync burst** | Many files touched in the same minute by OneDrive - not work |
| **`[to confirm]`** | Placeholder for anything not backed by evidence; never guessed |
| **Void** | Mark a record as replaced or removed; it stays in the ledger for history |
