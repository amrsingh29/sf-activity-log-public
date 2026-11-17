#!/usr/bin/env bash
# Install SF Activity Log for Open Worker (macOS).
#   1. Python venv + engine     -> <repo>/.venv, ~/.sf-activity-log/bin/{sfal,sfal-mcp}
#   2. Workflow files           -> ~/.sf-activity-log/{SKILL,NOTE}.md
#   3. Skills                   -> ~/.config/coworker/skills/{log-activity-note,sf-log,sf-log-setup}
#   4. MCP servers              -> ~/.config/coworker/mcp.json (merged; other servers kept)
#        sfal        read and prepare tools, no approval prompt
#        sfal-write  sfal_commit, sfal_note_save, sfal_setup_save_profile, sfal_account_add - Open Worker asks first
# Open Worker has no slash commands: it loads a skill when the AI judges it relevant, so the
# skill descriptions say "only when the user explicitly asks". Safe to re-run.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
OW="${COWORKER_HOME:-$HOME/.config/coworker}"
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
if [ ! -d "$OW" ]; then
  echo "Open Worker settings not found at $OW - install Open Worker and open it once first."
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

echo "==> Skills in $OW/skills"
for s in log-activity-note sf-log sf-log-setup sf-add-customer sf-docs-sync sf-docs-status; do
  mkdir -p "$OW/skills/$s"
  cp "$REPO/hosts/openworker/skills/$s/SKILL.md" "$OW/skills/$s/SKILL.md"
done

echo "==> MCP servers sfal + sfal-write in $OW/mcp.json"
"$REPO/.venv/bin/python" - "$OW/mcp.json" "$BIN/sfal-mcp" <<'PY'
import json, sys
from pathlib import Path
path, cmd = Path(sys.argv[1]), sys.argv[2]
data = json.loads(path.read_text()) if path.exists() and path.read_text().strip() else {}
if path.exists():
    path.with_suffix(".json.bak").write_text(path.read_text())
writes = ["sfal_commit", "sfal_note_save", "sfal_setup_save_profile", "sfal_account_add"]
servers = data.setdefault("mcpServers", {})
servers["sfal"] = {"command": cmd, "args": [], "exclude_tools": writes, "requires_approval": False}
servers["sfal-write"] = {"command": cmd, "args": [], "include_tools": writes, "requires_approval": True}
path.write_text(json.dumps(data, indent=2) + "\n")
print(f"   {path}: {', '.join(servers)}")
PY

echo
echo "Quit and reopen Open Worker, then ask: \"log my activity note: ...\" or \"sf-log last week\"."
echo "First run: allow Open Worker to access Calendars (Full Access) and to control Mail."
