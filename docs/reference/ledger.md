# Ledger reference

`<log folder>/ledger/ledger.csv` is the single source of truth. Every Excel file is built from
it. It opens in Excel, but **do not edit it by hand** - use a run ([Fix a record](../use/fix-a-record.md)).

## Rules

- Rows are only added, never deleted.
- A correction voids the old row (`voided`, `voided_by`) and adds a new one (`supersedes`).
- Every action is logged in `ledger/audit.log`.
- A lock file prevents two runs (or two Macs via OneDrive) writing at once.

## Columns

| # | Column | Meaning |
|---|---|---|
| 1 | `entry_id` | record ID, e.g. `A0012` |
| 2 | `owner` | Salesforce Primary Owner (from your profile) |
| 3 | `account_name` | Salesforce account |
| 4 | `account_kind` | customer, partner or internal |
| 5 | `activity_type` | one of 22, e.g. `07 · Product Demo` |
| 6 | `opportunity` | opportunity, if known |
| 7 | `no_opp_reason` | required when there is no opportunity |
| 8 | `status` | Completed, In Progress, Planned, Cancelled |
| 9 | `activity_date` | day delivered (latest day for long-running records) |
| 10 | `start_date` | first day, for Value Review / POC / RFP |
| 11 | `activity_hours` | delivery hours, above 0 |
| 12 | `prep_hours` | preparation hours |
| 13 | `notes` | Salesforce "Activity Hours Notes" |
| 14 | `solution_area` | AIOps, Discovery, ITSM, ESM, Other (`;`-separated) |
| 15 | `timezone` | e.g. `Asia/Singapore` |
| 16 | `evidence_refs` | evidence behind the record (`cal:…`, `mail:…`, `note:…`, `user:…`) |
| 17 | `consolidation_key` | links sessions of one Value Review / POC / RFP |
| 18 | `rule_pack_version` | rules it was checked against, e.g. `example-1.0` |
| 19 | `voided` | true if replaced or removed |
| 20 | `voided_by` | record that replaced it, or `manual: <reason>` |
| 21 | `supersedes` | record this one replaced |
| 22 | `run_id` | run that created it |
| 23 | `to_confirm` | open questions |
| 24 | `confidence` | High, Medium, Low |
| 25 | `added_on` | when it was written |

`user:` evidence means you stated it during review, e.g. `user:demo ran 2 hours`.
