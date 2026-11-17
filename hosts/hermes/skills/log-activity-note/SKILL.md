---
name: log-activity-note
description: SF Activity Log - capture what the user just did (a meeting, work, files) as a detailed activity note. Use ONLY when the user types /log-activity-note or explicitly asks to log or capture an activity note. Never on your own because a customer, meeting or email is mentioned.
version: 1.0.0
platforms: [macos]
---

# Log activity note

Log an activity note for what the user described with the command (if they described
nothing, offer today's meetings, emails and files to pick from).

The full workflow follows below this line; follow it exactly. Use the
`sfal` MCP tools for every engine operation (engine CLI fallback: `~/.sf-activity-log/bin/sfal`).
Save only after the user confirms the note.
