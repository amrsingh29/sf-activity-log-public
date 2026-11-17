"""Hermes host: skills carry the full workflow, and the installer adds sfal to config.yaml safely."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WITH_SERVERS = """# Hermes config
model:
  default: "cortex-max"
mcp_servers:
  github:
    command: "npx"
    args: ["-y", "x"]
skills:
  nudge_interval: 10
"""
NO_SERVERS = """model:
  default: "cortex-max"
# mcp_servers:
#   time:
#     command: "uvx"
"""


class TestHermesHost(unittest.TestCase):
    def install(self, config_text):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        hh = Path(tmp.name) / "hermes"
        hh.mkdir()
        (hh / "config.yaml").write_text(config_text)
        home = Path(tmp.name) / "home"
        (home / ".sf-activity-log").mkdir(parents=True)
        env = dict(os.environ, HERMES_HOME=str(hh), HOME=str(home))
        for _ in range(2):                               # re-running must not duplicate anything
            r = subprocess.run(["bash", str(ROOT / "hosts/hermes/install.sh")], env=env,
                               capture_output=True, text=True, timeout=600)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return hh

    def test_adds_sfal_next_to_existing_servers(self):
        hh = self.install(WITH_SERVERS)
        cfg = yaml.safe_load((hh / "config.yaml").read_text())
        self.assertEqual(set(cfg["mcp_servers"]), {"github", "sfal"})
        self.assertTrue(cfg["mcp_servers"]["sfal"]["command"].endswith("/.sf-activity-log/bin/sfal-mcp"))
        self.assertEqual(cfg["skills"], {"nudge_interval": 10})           # the rest untouched
        self.assertTrue(list(hh.glob("config.yaml.bak-before-sfal-*")))

    def test_creates_mcp_servers_when_only_commented(self):
        hh = self.install(NO_SERVERS)
        text = (hh / "config.yaml").read_text()
        self.assertIn("# mcp_servers:", text)                             # comments kept
        self.assertEqual(list(yaml.safe_load(text)["mcp_servers"]), ["sfal"])

    def test_skills_are_self_contained_and_explicit_only(self):
        hh = self.install(NO_SERVERS)
        for name, marker in (("log-activity-note", "## "), ("sf-log", "Hard rules"), ("sf-log-setup", "Setup"), ("sf-add-customer", "Add a customer")):
            text = (hh / "skills/sf-activity-log" / name / "SKILL.md").read_text()
            meta = yaml.safe_load(text.split("---")[1])
            self.assertEqual(meta["name"], name)
            self.assertIn("ONLY when the user types", meta["description"])
            self.assertEqual(meta["platforms"], ["macos"])
            self.assertIn("The full workflow follows below", text)
            self.assertIn(marker, text.split("The full workflow follows below", 1)[1])
        note = (hh / "skills/sf-activity-log/log-activity-note/SKILL.md").read_text()
        body = (ROOT / "skill/NOTE.md").read_text().split("---", 2)[-1].strip()[:200]
        self.assertIn(body, note)                                          # NOTE.md text, not a pointer


if __name__ == "__main__":
    unittest.main()
