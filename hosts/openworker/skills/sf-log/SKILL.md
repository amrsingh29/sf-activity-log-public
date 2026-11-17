---
name: sf-log
description: SF Activity Log - build the Salesforce-ready presales engineer activity log for a period (today, last week, October, YYYY-MM-DD to YYYY-MM-DD). Use ONLY when the user explicitly asks to log their week or period for Salesforce, or says "sf-log". Never on your own.
---

Build the user's Salesforce activity log for the period they named. If they named no
period, ask for one.

First read the file `~/.sf-activity-log/SKILL.md` in full, then follow it exactly. Use the
`sfal_*` MCP tools for every engine operation (the `sfal-write` server holds
`sfal_commit`). Never write to the ledger before the user approves the review table.
