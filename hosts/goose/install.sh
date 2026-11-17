#!/usr/bin/env bash
# Install SF Activity Log for Goose (macOS).
#   1. Engine + MCP server     -> <repo>/.venv, ~/.sf-activity-log/bin/{sfal,sfal-mcp}
#   2. Recipes                 -> ~/.config/goose/recipes/{log-activity-note,sf-log,sf-log-setup,sf-add-customer,sf-docs-sync,sf-docs-status}.yaml
# Each recipe loads only the sfal MCP extension. Safe to re-run. Does not touch your profile or data.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
GOOSE_DIR="${GOOSE_CONFIG_DIR:-$HOME/.config/goose}"
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
[ -x "$REPO/.venv/bin/python" ] || python3 -m venv "$REPO/.venv"
"$REPO/.venv/bin/pip" install -q -e "$REPO"

echo "==> Engine commands in $BIN"
mkdir -p "$BIN"
ln -sf "$REPO/.venv/bin/sfal" "$BIN/sfal"
ln -sf "$REPO/.venv/bin/sfal-mcp" "$BIN/sfal-mcp"

echo "==> Goose recipes"
"$REPO/.venv/bin/python" "$REPO/hosts/goose/make_recipes.py" "$GOOSE_DIR/recipes" "$BIN/sfal-mcp"
if command -v goose >/dev/null 2>&1; then
  for r in log-activity-note sf-log sf-log-setup sf-add-customer sf-docs-sync sf-docs-status; do
    goose recipe validate "$GOOSE_DIR/recipes/$r.yaml" >/dev/null && echo "   valid: $r"
  done
else
  echo "   (goose CLI not found - skipped validation; Goose Desktop will list the recipes under Recipes)"
fi

echo
if [ -f "$HOME/.sf-activity-log/profile.yaml" ]; then
  echo "Profile found. Run a period:"
  echo "  goose run --recipe sf-log --params period=\"last week\" -s"
else
  echo "No profile yet. Start setup:"
  echo "  goose run --recipe sf-log-setup -s"
fi
echo "Goose Desktop: Recipes -> 'SF Activity Log' -> Run (restart Goose if it was open)"
