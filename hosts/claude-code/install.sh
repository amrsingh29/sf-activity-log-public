#!/usr/bin/env bash
# Install SF Activity Log for Claude Code (macOS).
#   1. Python venv + engine          -> <repo>/.venv, ~/.sf-activity-log/bin/{sfal,sfal-mcp}
#   2. Workflow files                -> ~/.sf-activity-log/{SKILL,NOTE}.md
#   3. /log-activity-note, /sf-log, /sf-log-setup, /sf-add-customer, /sf-docs-sync, /sf-docs-status -> ~/.claude/commands (explicit use only)
#   4. MCP server "sfal"             -> Claude Code user scope
# Privacy: with Claude, the text the workflow reads goes to Anthropic, not Cortex.
# Safe to re-run. Does not touch your profile or data.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
CC="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
BIN="$HOME/.sf-activity-log/bin"

if ! command -v swiftc >/dev/null 2>&1; then
  echo "Apple Command Line Tools are missing (needed to read your calendar)."
  echo "Run:  xcode-select --install   then run this installer again."
  exit 1
fi
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
  echo "Python 3.11 or newer is needed (found: $(python3 --version 2>&1)). Install it with: brew install python"
  exit 1
fi
if ! command -v claude >/dev/null 2>&1; then
  echo "Claude Code (the claude command) is not installed."
  exit 1
fi

echo "==> Engine (Python venv)"
if [ ! -x "$REPO/.venv/bin/python" ]; then
  python3 -m venv "$REPO/.venv"
fi
"$REPO/.venv/bin/pip" install -q -e "$REPO"
mkdir -p "$BIN"
ln -sf "$REPO/.venv/bin/sfal" "$BIN/sfal"
ln -sf "$REPO/.venv/bin/sfal-mcp" "$BIN/sfal-mcp"

echo "==> Workflow files in $HOME/.sf-activity-log"
cp "$REPO/skill/SKILL.md" "$HOME/.sf-activity-log/SKILL.md"
cp "$REPO/skill/NOTE.md" "$HOME/.sf-activity-log/NOTE.md"
cp "$REPO/skill/DOCS.md" "$HOME/.sf-activity-log/DOCS.md"

echo "==> Claude Code commands in $CC/commands"
# Same files as OpenCode, plus disable-model-invocation: Claude Code would otherwise offer them
# to the model as skills - the workflow must run only when you type the command.
mkdir -p "$CC/commands"
for c in log-activity-note sf-log sf-log-setup sf-add-customer sf-docs-sync sf-docs-status; do
  awk 'NR==1 && /^---$/ {print; print "disable-model-invocation: true"; next} {print}' \
    "$REPO/hosts/opencode/commands/$c.md" > "$CC/commands/$c.md"
done

echo "==> MCP server sfal (user scope)"
if claude mcp get sfal >/dev/null 2>&1; then
  echo "   already registered"
else
  claude mcp add --scope user sfal "$BIN/sfal-mcp"
fi

echo
echo "Privacy: in Claude Code, meeting, email and note text goes to Anthropic, not Cortex."
echo "Check your company's policy before using it with customer data."
echo
echo "Then in a new Claude Code session:  /sf-log last week"
