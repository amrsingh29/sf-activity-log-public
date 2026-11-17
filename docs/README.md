# SF Activity Log

> Capture your work while it is fresh, and turn it into a Salesforce-ready activity log every
> week - following the your company's logging guide. You approve everything it logs.

## Two jobs, three commands

| When | Job | Goose (Desktop recipe) | OpenCode |
|---|---|---|---|
| Daily, after a meeting or piece of work | **Capture a note** | Log Activity Note | `/log-activity-note` |
| Weekly | **Log your week** → Excel to paste into Salesforce | SF Activity Log | `/sf-log last week` |
| Once, and when things change | **Set up your profile** | SF Activity Log - Setup | `/sf-log-setup` |

Claude Code, omp and Hermes use the same commands as OpenCode; in Open Worker you ask in words ("sf-log last week").

## Start here

Pick the AI tool you use and follow its page from top to bottom - it covers everything, from
installing the tool to your first weekly log.

| I use | Start with |
|---|---|
| Goose Desktop (app) - easiest | [Get started with Goose Desktop](start/goose-desktop.md) |
| Goose in the terminal | [Get started with Goose CLI](start/goose-cli.md) |
| OpenCode | [Get started with OpenCode](start/opencode.md) |
| Claude Code (data goes to Anthropic, not Cortex) | [Get started with Claude Code](start/claude-code.md) |
| Open Worker (desktop app, with Cortex) | [Get started with Open Worker](start/openworker.md) |
| omp (oh-my-pi, terminal) | [Get started with omp](start/omp.md) |
| Hermes Agent (terminal) | [Get started with Hermes](start/hermes.md) |

## Use it

| Task | Guide |
|---|---|
| Capture what you just did | [Capture a note](use/capture-a-note.md) |
| Log your week and paste into Salesforce | [Log your week](use/log-your-week.md) |
| See all notes, records and weeks in one page | [Browse your catalog](use/browse-the-catalog.md) |
| Fix or remove a logged record | [Fix a record](use/fix-a-record.md) |
| Run a past week or month again | [Re-run a period](use/rerun-a-period.md) |
| Use a Copilot, Word or Excel export | [Use exports](use/use-exports.md) |
| Add a new customer or partner, with its folder | [Add a customer](use/add-a-customer.md) |
| Add accounts, change folders or sources | [Update your profile](use/update-your-profile.md) |
| Make Word, PowerPoint and PDF files searchable | [Search your documents](use/search-your-documents.md) |
| Find those documents from every AI tool through GBrain | [Search your documents in GBrain](use/search-documents-in-gbrain.md) |
| Change your Cortex API key | [Change your Cortex key](use/change-cortex-key.md) |

Something wrong? [Troubleshooting](troubleshooting.md) · Questions? [FAQ](faq.md)

## Look it up

| Topic | Reference |
|---|---|
| Commands in every tool | [Commands](reference/commands.md) |
| Every profile setting | [Configuration](reference/configuration.md) |
| What a note contains | [Note format](reference/note-format.md) |
| What each source reads | [Sources](reference/sources.md) |
| logging guide rules and checks | [Rules](reference/rules.md) |
| Output folders and the Excel file | [Output](reference/output.md) |
| The ledger's 25 columns | [Ledger](reference/ledger.md) |
| Terms | [Glossary](reference/glossary.md) |

## Understand it

| Topic | Page |
|---|---|
| The layers, the module map and what a run leaves on disk | [Architecture](understand/architecture.md) |
| The daily-to-weekly loop, with an example | [How it works](understand/how-it-works.md) |
| What the AI does and never does | [AI and engine](understand/ai-and-engine.md) |
| Guarantees: approval, history, where it writes | [Safety](understand/safety.md) |
| Goose, OpenCode, Claude Code, Open Worker, omp, Hermes and adding other tools | [AI tools](understand/ai-tools.md) |

Maintainers: [Design](maintainers/design.md) · [Decisions](maintainers/decisions.md) ·
[Changelog](maintainers/changelog.md) · [Contributing](maintainers/contributing.md) · [Test the setup](maintainers/test-setup.md)
