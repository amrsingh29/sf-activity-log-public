---
name: sf-log
description: SF Activity Log - build the Salesforce-ready presales engineer activity log for a period (today, last week, October, YYYY-MM-DD to YYYY-MM-DD). Use ONLY when the user types /sf-log or explicitly asks to log their week or period for Salesforce. Never on your own.
version: 1.0.0
platforms: [macos]
---

# Log the period for Salesforce

Build the user's Salesforce activity log for the period they named with the command. If they
named no period, ask for one.

The full workflow follows below this line; follow it exactly. Use the
`sfal` MCP tools for every engine operation (engine CLI fallback: `~/.sf-activity-log/bin/sfal`).
Never commit to the ledger before the user approves the review table.
