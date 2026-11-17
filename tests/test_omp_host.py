"""omp host: the installer copies the OpenCode commands and merges ~/.omp/agent/mcp.json."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestOmpHost(unittest.TestCase):
    def test_installer_copies_commands_and_merges_mcp(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = Path(tmp) / "agent"
            agent.mkdir()
            (agent / "mcp.json").write_text(json.dumps({"mcpServers": {"other": {"type": "stdio", "command": "x"}}}))
            home = Path(tmp) / "home"
            (home / ".sf-activity-log").mkdir(parents=True)
            env = dict(os.environ, OMP_AGENT_DIR=str(agent), HOME=str(home))
            r = subprocess.run(["bash", str(ROOT / "hosts/omp/install.sh")], env=env,
                               capture_output=True, text=True, timeout=600)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            servers = json.loads((agent / "mcp.json").read_text())["mcpServers"]
            self.assertEqual(set(servers), {"other", "sfal"})
            self.assertEqual(servers["sfal"]["type"], "stdio")
            self.assertTrue(servers["sfal"]["command"].endswith("/.sf-activity-log/bin/sfal-mcp"))
            self.assertTrue((agent / "mcp.json.bak").exists())
            for c in ("log-activity-note", "sf-log", "sf-log-setup"):
                self.assertEqual((agent / "commands" / f"{c}.md").read_text(),
                                 (ROOT / "hosts/opencode/commands" / f"{c}.md").read_text())

    def test_refuses_without_omp(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, OMP_AGENT_DIR=str(Path(tmp) / "missing"))
            r = subprocess.run(["bash", str(ROOT / "hosts/omp/install.sh")], env=env,
                               capture_output=True, text=True, timeout=120)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("omp settings not found", r.stdout)


if __name__ == "__main__":
    unittest.main()
