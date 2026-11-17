---
name: sf-add-customer
description: SF Activity Log - add a customer or partner to the user's profile and create its folder. Use ONLY when the user explicitly asks to add a customer to their SF Activity Log, or says "sf-add-customer".
---

Add a customer or partner to the user's SF Activity Log profile, with its folder.

First read the file `~/.sf-activity-log/SKILL.md` in full, then follow its **Add a customer** section
exactly: ask only for what is missing, show the plan, and write only after the user says yes
(`sfal_account_add` with `confirm` true is on the `sfal-write` server).
