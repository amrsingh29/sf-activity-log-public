# Add a customer

> Add one customer or partner to your profile, with its folder, in one step.
> You approve the plan before anything is written.

## In your AI tool

Goose Desktop: Recipes → **SF Activity Log - Add Customer** → ▶
(terminal: `goose run --recipe sf-add-customer -s`; OpenCode and Claude Code: `/sf-add-customer`;
Open Worker: ask *"add customer ACME Bank"*).

The assistant asks only for what is missing: the name, then the country folder if your workspace
puts customers one level down. Then it shows the plan:

```text
Add customer ACME Bank (customer, aliases: ACME)
  Profile:  add the account; the current profile is backed up first
  Folder:   Malaysia/ACME Bank        (create)
  Layout:   _ActivityLogging          (create)
Proceed? yes / no
```

Answer yes and it writes. Nothing is written before that.

## What it does and does not do

- Adds one account to `accounts:` in your profile. Existing accounts are kept.
- Creates `<country>/<name>/_ActivityLogging/`. That is the folder notes for this customer go to.
- Reuses the folder if it already exists, and never changes files in it.
- Refuses a name or alias that another account already uses, and tells you which account it is.
- Keeps a backup of the profile (`profile.yaml.bak-<time>`) and records the change in the audit log.

## From the terminal

```bash
~/.sf-activity-log/bin/sfal account-add "ACME Bank" --country Malaysia --alias ACME --domain acme.com
```

That shows the plan. Add `--yes` to apply it.

## Extra folders

The default layout is `_ActivityLogging` only. To add more, pass them when you add the customer:

```bash
~/.sf-activity-log/bin/sfal account-add "ACME Bank" --country Malaysia --extra-folder Proposals
```

Next: [Update your profile](update-your-profile.md)
