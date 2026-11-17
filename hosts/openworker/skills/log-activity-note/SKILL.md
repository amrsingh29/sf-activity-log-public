---
name: log-activity-note
description: SF Activity Log - capture what the user just did (a meeting, work, files) as a detailed activity note. Use ONLY when the user explicitly asks to log, capture or note an activity or says "log activity note". Never on your own because a customer, meeting or email is mentioned.
---

Log an activity note for what the user described in their message (if they described
nothing, offer today's meetings, emails and files to pick from).

First read the file `~/.sf-activity-log/NOTE.md` in full, then follow it exactly. Use the
`sfal_*` MCP tools for every engine operation (the `sfal-write` server holds
`sfal_note_save`). Save only after the user confirms the note.
