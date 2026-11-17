"""install-all: runs the installer of every AI tool found, skips the rest, Claude Code only when opted in."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OVERRIDES = ("GOOSE_CONFIG_DIR", "OPENCODE_CONFIG_DIR", "COWORKER_HOME", "OMP_AGENT_DIR",
             "HERMES_HOME", "CLAUDE_CONFIG_DIR", "OMP_AGENT_DIR")


class TestInstallAll(unittest.TestCase):
    def run_all(self, home: Path, *args):
        env = {k: v for k, v in os.environ.items() if k not in OVERRIDES}
        env["HOME"] = str(home)
        return subprocess.run(["bash", str(ROOT / "hosts/install-all.sh"), *args], env=env,
                              capture_output=True, text=True, timeout=900)

    def test_installs_only_the_tools_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".sf-activity-log").mkdir()
            (home / ".omp" / "agent").mkdir(parents=True)
            (home / ".hermes").mkdir()
            (home / ".hermes" / "config.yaml").write_text("model:\n  default: cortex-max\n")
            r = self.run_all(home)
            self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
            self.assertIn("Installed/updated: omp Hermes", r.stdout)
            self.assertIn("Claude Code (opt-in: --with-claude)", r.stdout)
            self.assertTrue((home / ".omp/agent/commands/sf-log.md").exists())
            self.assertTrue((home / ".hermes/skills/sf-activity-log/sf-log/SKILL.md").exists())
            self.assertFalse((home / ".config/opencode").exists())        # not created for missing tools

    def test_nothing_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self.run_all(Path(tmp))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("No supported AI tool found", r.stdout)


if __name__ == "__main__":
    unittest.main()
