#!/usr/bin/env bash
# Install SF Activity Log for OpenCode (macOS).
#   1. Python venv + engine          -> <repo>/.venv
#   2. Stable engine path            -> ~/.sf-activity-log/bin/sfal
#   3. Workflow files                -> ~/.sf-activity-log/{SKILL,NOTE}.md (not auto-loaded skills)
#   4. /log-activity-note, /sf-log, /sf-log-setup, /sf-add-customer, /sf-docs-sync, /sf-docs-status -> ~/.config/opencode/commands
# Safe to re-run. Does not touch your profile or data.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
OC="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}"
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

echo "==> Engine (Python venv)"
if [ ! -x "$REPO/.venv/bin/python" ]; then
  python3 -m venv "$REPO/.venv"
fi
"$REPO/.venv/bin/pip" install -q -e "$REPO"

echo "==> Engine command at $BIN/sfal"
mkdir -p "$BIN"
ln -sf "$REPO/.venv/bin/sfal" "$BIN/sfal"
ln -sf "$REPO/.venv/bin/sfal-mcp" "$BIN/sfal-mcp"

echo "==> Workflow file at $HOME/.sf-activity-log/SKILL.md"
# Deliberately NOT an OpenCode skill: skills can be auto-loaded by the AI whenever a request
# looks related. The workflow runs only when you type /sf-log or /sf-log-setup.
cp "$REPO/skill/SKILL.md" "$HOME/.sf-activity-log/SKILL.md"
cp "$REPO/skill/NOTE.md" "$HOME/.sf-activity-log/NOTE.md"
cp "$REPO/skill/DOCS.md" "$HOME/.sf-activity-log/DOCS.md"
if [ -d "$OC/skills/sf-activity-log" ]; then
  rm -rf "$OC/skills/sf-activity-log"
  echo "   removed the old auto-loadable skill ($OC/skills/sf-activity-log)"
fi

echo "==> OpenCode commands /log-activity-note, /sf-log, /sf-log-setup, /sf-add-customer, /sf-docs-sync, /sf-docs-status in $OC/commands"
mkdir -p "$OC/commands"
for c in log-activity-note sf-log sf-log-setup sf-add-customer sf-docs-sync sf-docs-status; do
  cp "$REPO/hosts/opencode/commands/$c.md" "$OC/commands/$c.md"
done

echo
if [ -f "$HOME/.sf-activity-log/profile.yaml" ]; then
  echo "Profile found. Checking environment:"
  "$BIN/sfal" doctor || true
else
  echo "Next: in OpenCode, run  /sf-log-setup"
fi
echo
echo "Then in OpenCode:  /sf-log last week"
