# Test the setup in isolation

Use this to run the first-time setup as a new presales user would, without touching your real
profile, notes or folders. Run it in a new Terminal window.

**Rules**

- Never point the test workspace at your real OneDrive folder.
- The test profile must set its own `data_dir` and `workspace.root` inside `~/sfal-test`
  **before** any engine command runs. Otherwise the engine falls back to your real data folder.
- Keep the real profile at `~/.sf-activity-log/profile.yaml`. The test uses its own file.

## 1. Mark the time and make a scratch workspace

```bash
touch ~/sfal-test-marker
mkdir -p ~/sfal-test/ws/Malaysia/adatum ~/sfal-test/ws/Vietnam/LITWARE ~/sfal-test/ws/NewBank
```

## 2. Point sfal at the test profile (this window only)

```bash
export SFAL_PROFILE=~/sfal-test/profile.yaml
```

## 3. Scan

```bash
~/.sf-activity-log/bin/sfal setup-scan --root ~/sfal-test/ws
```

Expect progress lines on stderr (folders, calendar, mail, finished) and JSON on stdout.
The scan must list `Malaysia/adatum` and `Vietnam/LITWARE` as customer folder candidates.
`NewBank` is not proposed yet, because it has no calendar or mail activity.

## 4. Run the interview

Start your AI tool from this same window, then run:

```text
/sf-log-setup
```

- When asked where to write the profile, answer `~/sfal-test/profile.yaml`.
- When asked for the workspace folder, answer `~/sfal-test/ws`.
- Do not copy your existing accounts over.
- Accept the folder-backed accounts (adatum and LITWARE) and pick the customers you want.

## 5. Check the saved test profile

```bash
grep -n "data_dir\|root:" ~/sfal-test/profile.yaml
```

Both lines must point inside `~/sfal-test`. If they don't, stop and fix the profile first.

```bash
~/.sf-activity-log/bin/sfal doctor
~/.sf-activity-log/bin/sfal note-targets adatum
~/.sf-activity-log/bin/sfal note-targets LITWARE
```

Expect `doctor` to show the test profile path. Expect both `note-targets` to point at
`~/sfal-test/ws/Malaysia/adatum` and `~/sfal-test/ws/Vietnam/LITWARE` with `_ActivityLogging/`.

## 6. Confirm the real data was not touched

```bash
find ~/Library/CloudStorage/OneDrive-MyCompany/Customers -newer ~/sfal-test-marker -not -name ".DS_Store"
```

Expect no output. Any file listed was changed during the test; check it before continuing.

```bash
diff ~/.sf-activity-log/profile.yaml.bak-before-litware ~/.sf-activity-log/profile.yaml
```

Expect only the LITWARE entry, or no output if the backup is the same as the current profile.

## 7. Clean up

```bash
unset SFAL_PROFILE
rm -rf ~/sfal-test ~/sfal-test-marker
```

## Pass criteria

- Scan shows adatum and LITWARE as candidates, with progress lines.
- The saved test profile's `data_dir` and `workspace.root` are inside `~/sfal-test`.
- `doctor` and `note-targets` point at the test folders.
- Step 6 finds nothing in the real Project folder.
