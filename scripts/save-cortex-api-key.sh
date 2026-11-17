#!/bin/zsh
# Save (or update) the Cortex API key in the macOS login Keychain.
# The key is typed at a hidden prompt; it is never written to a file or shown on screen.
#
# Usage:  ./save-cortex-api-key.sh          save / replace the key
#         ./save-cortex-api-key.sh --check  confirm a key is stored (shows a masked preview)

SERVICE="cortex-api-key"

if [[ "$1" == "--check" ]]; then
  key=$(security find-generic-password -a "$USER" -s "$SERVICE" -w 2>/dev/null)
  if [[ -n "$key" ]]; then
    echo "Stored in Keychain: ${key[1,6]}…${key[-4,-1]} (${#key} chars)"
  else
    echo "No Cortex API key found in Keychain (service: $SERVICE)."; exit 1
  fi
  exit 0
fi

echo "Paste your Cortex API key and press Enter (input is hidden)."
echo "macOS will ask for it twice: 'password data for new item' and 'retype'."
security add-generic-password -U -a "$USER" -s "$SERVICE" -l "Cortex API key" -w \
  && echo "Saved to Keychain as service '$SERVICE'." \
  && "$0" --check
