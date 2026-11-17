# AI and engine

The **engine** is ordinary code: it reads, filters, checks and writes. The **AI** (Cortex in
Goose, OpenCode, omp, Hermes, Open Worker or Claude Code) does the parts that need judgment and language.

## The AI does

| Task | Example |
|---|---|
| Group evidence into records | meeting + agenda email + prep deck → one Product Demo |
| Choose the activity type | from the 22 logging guide definitions |
| Write the Notes | "what was done, in detail", from titles, people and previews |
| Resolve or flag ambiguity | internal or customer? demo inside a POC? → asks you or `[to confirm]` |
| Read prose exports | pulls dated items out of a Copilot summary, quoting each line |
| Fix rejected records | adjusts a record the validator rejected and re-submits |
| Run the conversation | asks your questions, turns *"make row 3 a demo"* into changes |
| Run setup | interviews you and proposes your profile |

## The engine does

| Task | Why not the AI |
|---|---|
| Read calendar, mail, notes, files, exports | must be complete and identical every run |
| Drop noise (cancelled, declined, lunch, newsletters, sync bursts) | rules, not judgment |
| Match accounts | your account list is the source of truth |
| Decide which items need your call, with defaults | same questions in every AI tool |
| Compute hours and totals | exact durations; AI arithmetic is unreliable |
| Enforce the logging guide rules | a rule must not depend on the model remembering it |
| Write the ledger and the Excel file | only the engine writes, append-only |

## What the AI can never do

- Write the ledger directly - only `commit` writes, and only with the approval code.
- Log hours beyond the evidence - unless you state them (recorded as `user:` evidence).
- Invent an account, date or name - the validator rejects anything without evidence.
- Read all your email. The weekly log sees subjects, domains and a short preview; Capture a note
  also reads the full text of the emails (and invite descriptions) for the items you are noting.

## Without the AI

The engine still collects, filters, matches accounts and checks records. You would choose the
types and write the notes yourself - which is exactly the part the AI saves you.
