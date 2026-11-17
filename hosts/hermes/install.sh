#!/usr/bin/env bash
# Install SF Activity Log for Hermes Agent (macOS).
#   1. Python venv + engine     -> <repo>/.venv, ~/.sf-activity-log/bin/{sfal,sfal-mcp}
#   2. Workflow files           -> ~/.sf-activity-log/{SKILL,NOTE}.md
#   3. Skills (= slash commands /log-activity-note, /sf-log, /sf-log-setup)
#                               -> ~/.hermes/skills/sf-activity-log/<skill>/SKILL.md
#   4. MCP server "sfal"        -> mcp_servers in ~/.hermes/config.yaml (added once; backup kept)
# Hermes lists skills for the AI as well, so the descriptions say "only when the user types it".
# Safe to re-run. Does not touch your profile or data.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
HH="${HERMES_HOME:-$HOME/.hermes}"
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
if [ ! -f "$HH/config.yaml" ]; then
  echo "Hermes settings not found at $HH/config.yaml - install Hermes and run it once first."
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

echo "==> Skills in $HH/skills/sf-activity-log (each carries the full workflow text)"
# Header from hosts/hermes/skills/<name>/SKILL.md + the workflow body from skill/{SKILL,NOTE}.md,
# so the skill works without a file read (single source: regenerated on every install).
for pair in log-activity-note:NOTE.md sf-log:SKILL.md sf-log-setup:SKILL.md sf-add-customer:SKILL.md sf-docs-sync:DOCS.md sf-docs-status:DOCS.md; do
  s="${pair%%:*}"; src="${pair##*:}"
  mkdir -p "$HH/skills/sf-activity-log/$s"
  { cat "$REPO/hosts/hermes/skills/$s/SKILL.md"; printf '\n---\n\n'
    awk 'NR==1 && /^---$/ {fm=1; next} fm && /^---$/ {fm=0; next} !fm' "$REPO/skill/$src"
  } > "$HH/skills/sf-activity-log/$s/SKILL.md"
done

echo "==> MCP server sfal in $HH/config.yaml"
"$REPO/.venv/bin/python" - "$HH/config.yaml" "$BIN/sfal-mcp" <<'PY'
import re, shutil, sys, time
import yaml
path, cmd = sys.argv[1], sys.argv[2]
text = open(path, encoding="utf-8").read()
servers = (yaml.safe_load(text) or {}).get("mcp_servers") or {}
if "sfal" in servers:
    print("   already configured")
    sys.exit(0)
shutil.copy2(path, f"{path}.bak-before-sfal-{time.strftime('%Y%m%d-%H%M%S')}")
entry = f'  sfal:\n    command: "{cmd}"\n    args: []\n'
m = re.search(r"(?m)^mcp_servers:[ \t]*(\{\})?[ \t]*$", text)
if m and not m.group(1):        # a real mcp_servers block: add sfal as its first entry
    text = text[:m.end()] + "\n" + entry.rstrip("\n") + text[m.end():]
elif m:                         # mcp_servers: {}  ->  a block with sfal
    text = text[:m.start()] + "mcp_servers:\n" + entry.rstrip("\n") + text[m.end():]
else:                           # no mcp_servers yet (comments do not count)
    text = text.rstrip("\n") + "\n\n# MCP servers (added by SF Activity Log's installer)\nmcp_servers:\n" + entry
yaml.safe_load(text)            # never leave an unreadable config behind
open(path, "w", encoding="utf-8").write(text)
print("   added")
PY

echo
echo "Then in Hermes:  /sf-log last week   ·   /log-activity-note <what you did>"
