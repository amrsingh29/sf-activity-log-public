#!/usr/bin/env bash
# Install or update SF Activity Log in every AI tool found on this Mac.
#   Goose · OpenCode · Open Worker · omp · Hermes   -> installed when the tool's settings folder exists
#   Claude Code                                      -> only refreshed if SF Activity Log is already set up
#                                                       there (data goes to Anthropic, not Cortex), or
#                                                       added with --with-claude
# Run it after pulling a new version, or after changing skill/SKILL.md or skill/NOTE.md.
# Safe to re-run. Does not touch your profile or data.
set -uo pipefail

HOSTS="$(cd "$(dirname "$0")" && pwd)"
WITH_CLAUDE=0
[ "${1:-}" = "--with-claude" ] && WITH_CLAUDE=1

declare -a ran=() skipped=() failed=()
run() {  # run NAME INSTALLER
  echo; echo "################ $1"
  if bash "$2"; then ran+=("$1"); else failed+=("$1"); fi
}

[ -d "${GOOSE_CONFIG_DIR:-$HOME/.config/goose}" ]        && run "Goose"       "$HOSTS/goose/install.sh"      || skipped+=("Goose")
[ -d "${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}" ]  && run "OpenCode"    "$HOSTS/opencode/install.sh"   || skipped+=("OpenCode")
[ -d "${COWORKER_HOME:-$HOME/.config/coworker}" ]        && run "Open Worker" "$HOSTS/openworker/install.sh" || skipped+=("Open Worker")
[ -d "${OMP_AGENT_DIR:-$HOME/.omp/agent}" ]              && run "omp"         "$HOSTS/omp/install.sh"        || skipped+=("omp")
[ -f "${HERMES_HOME:-$HOME/.hermes}/config.yaml" ]       && run "Hermes"      "$HOSTS/hermes/install.sh"     || skipped+=("Hermes")
if [ -f "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/commands/sf-log.md" ] || [ "$WITH_CLAUDE" = 1 ]; then
  run "Claude Code" "$HOSTS/claude-code/install.sh"
else
  skipped+=("Claude Code (opt-in: --with-claude)")
fi

echo; echo "================ SF Activity Log install summary"
echo "Installed/updated: ${ran[*]:-none}"
echo "Not found/skipped: ${skipped[*]:-none}"
if [ ${#failed[@]} -gt 0 ]; then
  echo "FAILED:            ${failed[*]}  - see the output above"
  exit 1
fi
[ ${#ran[@]} -gt 0 ] || echo "No supported AI tool found - install one first (see docs/README.md)."
echo "Restart the AI tools you had open so they load the update."
