# SF Activity Log - common tasks. Run `make help`.
PY := .venv/bin/python

.PHONY: help install install-all install-goose install-opencode install-claude install-openworker install-omp install-hermes test docs doctor clean

help:              ## list the tasks
	@grep -E '^[a-z-]+:.*##' Makefile | sed -E 's/:.*## /\t/'

install:           ## every AI tool found on this Mac (Claude Code only if already set up)
	bash hosts/install-all.sh

install-all: install

install-goose:     ## engine + Goose recipes only
	bash hosts/goose/install.sh

install-opencode:  ## engine + OpenCode commands only
	bash hosts/opencode/install.sh

install-claude:    ## engine + Claude Code commands and MCP server (data goes to Anthropic)
	bash hosts/claude-code/install.sh

install-openworker: ## engine + Open Worker skills and MCP servers
	bash hosts/openworker/install.sh

install-omp:       ## engine + omp commands and MCP server
	bash hosts/omp/install.sh

install-hermes:    ## engine + Hermes skills and MCP server
	bash hosts/hermes/install.sh

test:              ## run the test suite (no Mail/Calendar access needed)
	@test -x $(PY) || python3 -m venv .venv
	@$(PY) -m pip install -q -e .
	$(PY) -m unittest discover -s tests

docs:              ## regenerate docs/reference/rules.md from the rule pack
	$(PY) scripts/gen_docs.py

doctor:            ## check the environment and your profile
	~/.sf-activity-log/bin/sfal doctor

clean:             ## remove caches (keeps .venv, your profile and your log folder)
	rm -rf src/*.egg-info
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
