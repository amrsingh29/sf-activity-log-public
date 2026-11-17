# Change your Cortex key

> Replace your Cortex API key (rotation or a new key) and make every AI tool use it.
> About 2 minutes.

**Before you start:** have the new key ready. It is stored only in the macOS Keychain.

## Steps

1. Save the new key (replaces the old one; paste at the hidden prompt, asked twice):

   ```bash
   security add-generic-password -U -a "$USER" -s cortex-api-key -l "Cortex API key" -w
   ```

   Or use the helper: `~/Developer/sf-activity-log/scripts/save-cortex-api-key.sh`.
2. Check it (masked preview):

   ```bash
   ~/Developer/sf-activity-log/scripts/save-cortex-api-key.sh --check
   ```

3. Refresh your tool:

   | Tool | Do |
   |---|---|
   | Goose Desktop | Settings → Models → Cortex → paste the new key |
   | Goose CLI | open a new terminal |
   | OpenCode | open a new terminal, then `opencode service restart` |
   | omp | nothing - it reads the key from the Keychain at every start; start a new session |
   | Hermes | Settings → Providers → OpenAI API → paste the new key (or `OPENAI_API_KEY` in `~/.hermes/.env`), then quit and reopen |
   | Open Worker | update the key in Open Worker's model settings for Cortex, then quit and reopen |

**You'll see:** your tool answers again. A 401 error means it still has the old key - repeat
step 3.

Never put the key in `~/.zshrc`, a config file or a repository - only the Keychain.

To remove the key: `security delete-generic-password -a "$USER" -s cortex-api-key`.

Next: [Troubleshooting](../troubleshooting.md)
