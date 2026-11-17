# Contributing

The maintainer guide - layout, common changes, docs rules - is
[docs/maintainers/contributing.md](docs/maintainers/contributing.md). AI coding agents: read
[AGENTS.md](AGENTS.md) first.

## Quick setup

```bash
git clone https://github.com/amrsingh29/sf-activity-log-public.git
cd sf-activity-log
make test
```

## Before you open a pull request

- `make docs` and `make test` pass.
- New check, command, MCP tool or profile setting is documented (the docs test checks).
- Fictional names only (ACME Bank, Globex, Initech).
- Nothing that writes the ledger without the approval code - see [SECURITY.md](SECURITY.md).
- Entry in the [changelog](docs/maintainers/changelog.md); design choices in
  [decisions](docs/maintainers/decisions.md).

## Reporting a problem

Open an issue with the bug template: what you ran, what you expected, what you got, and the
output of `~/.sf-activity-log/bin/sfal doctor`. Remove customer names and email content first.
