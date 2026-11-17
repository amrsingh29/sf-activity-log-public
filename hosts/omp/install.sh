#!/usr/bin/env bash
# Install SF Activity Log for omp (oh-my-pi) on macOS.
#   1. Python venv + engine     -> <repo>/.venv, ~/.sf-activity-log/bin/{sfal,sfal-mcp}
#   2. Workflow files           -> ~/.sf-activity-log/{SKILL,NOTE}.md
#   3. /log-activity-note, /sf-log, /sf-log-setup, /sf-add-customer, /sf-docs-sync, /sf-docs-status -> ~/.omp/agent/commands (same files as OpenCode)
#   4. MCP server "sfal"        -> ~/.omp/agent/mcp.json (merged; other servers kept)
# omp runs commands only when you type them. Safe to re-run. Does not touch your profile or data.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
AGENT="${OMP_AGENT_DIR:-$HOME/.omp/agent}"
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
if [ ! -d "$AGENT" ]; then
  echo "omp settings not found at $AGENT - install omp and run it once first."
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

echo "==> omp commands /log-activity-note, /sf-log, /sf-log-setup, /sf-add-customer, /sf-docs-sync, /sf-docs-status in $AGENT/commands"
mkdir -p "$AGENT/commands"
for c in log-activity-note sf-log sf-log-setup sf-add-customer sf-docs-sync sf-docs-status; do
  cp "$REPO/hosts/opencode/commands/$c.md" "$AGENT/commands/$c.md"
done

echo "==> MCP server sfal in $AGENT/mcp.json"
"$REPO/.venv/bin/python" - "$AGENT/mcp.json" "$BIN/sfal-mcp" <<'PY'
import json, sys
from pathlib import Path
path, cmd = Path(sys.argv[1]), sys.argv[2]
text = path.read_text() if path.exists() else ""
data = json.loads(text) if text.strip() else {}
if text.strip():
    path.with_suffix(".json.bak").write_text(text)
data.setdefault("mcpServers", {})["sfal"] = {"type": "stdio", "command": cmd, "args": []}
path.write_text(json.dumps(data, indent=2) + "\n")
print(f"   {path}: {', '.join(data['mcpServers'])}")
PY

echo
echo "Then in omp:  /sf-log last week   ·   /log-activity-note <what you did>"
