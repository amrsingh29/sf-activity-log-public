# Update your profile

> Add accounts, ignore personal blocks, turn sources on or off, or change folders.
> Changes apply on the next run.

## Easiest: re-run setup

Goose Desktop: Recipes → **SF Activity Log - Setup** → ▶
(terminal: `goose run --recipe sf-log-setup -s`; OpenCode: `/sf-log-setup`).

It loads your current profile, shows what changed in your folders and mail, and saves a new
version after you confirm. The previous file is kept as `profile.yaml.bak-<date>`.

## New customer?

Use [Add a customer](add-a-customer.md): it adds one account and its folder, and
shows you the plan before it writes anything.

## Or edit the file

Open `~/.sf-activity-log/profile.yaml` in any editor. Changes apply on the next run.
The file is checked on every run; mistakes are reported with the line that is wrong.

### Add an account

```yaml
accounts:
  - { name: ACME Bank, kind: customer, aliases: [ACME, ACME-2026-RFP], domains: [acme.com] }
  - { name: Initech, kind: partner, domains: [initech.com] }
```

- `name` - exactly as in Salesforce
- `kind` - `customer` or `partner` (partner deals are logged under the customer)
- `aliases` - other spellings in folder names and meeting titles
- `domains` - their email domains

### Ignore a recurring personal block

```yaml
sources:
  calendar:
    ignore_titles: ["my day planning", "lunch*", "focus time"]
```

### Turn a source on or off

```yaml
sources:
  files:
    enabled: false
```

Or for one run only - ask *"run last week without files"*.

### Read more mailboxes

```yaml
sources:
  email:
    mailboxes: ["Sent Items", "Inbox"]
```

## Check it

```bash
~/.sf-activity-log/bin/sfal doctor
```

Shows each enabled source and whether it can be read.

Next: [Configuration reference](../reference/configuration.md)
