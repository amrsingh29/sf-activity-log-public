# FAQ

> Short answers to common questions. Each links to the page with the details.

**Does it upload to Salesforce?**
No. It produces an Excel file with records in Salesforce form order; you paste them.
[Log your week](use/log-your-week.md)

**Can it log something without my approval?**
No. Nothing reaches the ledger until you approve the review table, and the approval is tied to
exactly what you saw. Notes are saved only after you say yes. [Safety](understand/safety.md)

**Will it make up hours or names?**
No. Hours come from meetings or from you; anything unverified is marked `[to confirm]` and kept
out of the paste-ready sheet. [AI and engine](understand/ai-and-engine.md)

**Who sees my data?**
Your company AI (Cortex) sees meeting titles, attendee names, email subjects and the text of the
emails a note is about. Nothing is sent anywhere else - unless you run it in Claude Code, which
sends the same text to Anthropic instead. [Safety](understand/safety.md)

**Can I use it in Claude Code?**
Yes - same commands, same profile and ledger. What it reads then goes to Anthropic, not Cortex;
check your company's policy first. [Get started with Claude Code](start/claude-code.md)

**I don't keep one folder per customer. Does it still work?**
Yes. Notes are saved centrally by default and every note records its account. Folders are only a
hint. [Capture a note](use/capture-a-note.md#where-notes-are-saved)

**What is the difference between a note and a record?**
A note is your detailed account of what happened (daily). A record is one Salesforce activity
(weekly) - built from notes, meetings and email. [How it works](understand/how-it-works.md)

**I forgot to run it for three weeks.**
Run the period you missed, e.g. `2026-09-21 to 2026-10-11`. Nothing is logged twice.
[Re-run a period](use/rerun-a-period.md)

**A record is wrong after I logged it.**
Ask for the fix in plain words during a run; the old record is voided, a new one added.
[Fix a record](use/fix-a-record.md)

**Can I move or rename notes and customer folders?**
Yes. A note keeps its identity when it moves: notes already logged stay logged and are never
offered again. Only copies are a problem - two files with the same note count as two notes.
[Note format](reference/note-format.md)

**Does it work on Windows?**
Not yet - it needs macOS Calendar and Mail. Windows support is planned.

**Which AI tool should I use?**
Goose Desktop is the easiest. Every tool does the same jobs on the same profile and ledger, so you
can switch any time; with Claude Code your data goes to Anthropic instead of Cortex.
[Start here](README.md#start-here)

**Something isn't working.**
Run `~/.sf-activity-log/bin/sfal doctor`, then see [Troubleshooting](troubleshooting.md).
