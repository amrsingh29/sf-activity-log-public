"""Open Worker host: skills parse the way Open Worker reads them, and the installer merges mcp.json."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "hosts" / "openworker" / "skills"


def parse_like_openworker(md: Path) -> dict:
    """Open Worker's frontmatter reader (coworker/skills/base.py): 'key: value' lines between --- fences."""
    text = md.read_text(encoding="utf-8")
    out = {"name": md.parent.name, "description": ""}
    end = text.find("\n---", 3)
    for line in text[3:end].splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip().lower()] = v.strip()
    out["body"] = text[end + 4:].strip()
    return out


class TestOpenWorkerHost(unittest.TestCase):
    def test_skills_parse_and_are_explicit_only(self):
        names = sorted(p.name for p in SKILLS.iterdir())
        self.assertEqual(names, ["log-activity-note", "sf-add-customer", "sf-docs-status", "sf-docs-sync", "sf-log", "sf-log-setup"])
        for n in names:
            s = parse_like_openworker(SKILLS / n / "SKILL.md")
            self.assertEqual(s["name"], n)
            self.assertIn("ONLY when the user explicitly", s["description"])   # no slash commands there
            self.assertIn("~/.sf-activity-log/", s["body"])                     # one workflow file, not a copy

    def test_installer_merges_mcp_json_and_keeps_other_servers(self):
        with tempfile.TemporaryDirectory() as tmp:
            ow = Path(tmp) / "coworker"
            ow.mkdir()
            (ow / "mcp.json").write_text(json.dumps({"mcpServers": {"github": {"url": "https://example.com/mcp"}}}))
            home = Path(tmp) / "home"
            (home / ".sf-activity-log").mkdir(parents=True)
            env = dict(os.environ, COWORKER_HOME=str(ow), HOME=str(home))
            r = subprocess.run(["bash", str(ROOT / "hosts/openworker/install.sh")], env=env,
                               capture_output=True, text=True, timeout=600)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            servers = json.loads((ow / "mcp.json").read_text())["mcpServers"]
            self.assertEqual(set(servers), {"github", "sfal", "sfal-write"})
            writes = {"sfal_commit", "sfal_note_save", "sfal_setup_save_profile", "sfal_account_add"}
            self.assertEqual(set(servers["sfal"]["exclude_tools"]), writes)
            self.assertFalse(servers["sfal"]["requires_approval"])
            self.assertEqual(set(servers["sfal-write"]["include_tools"]), writes)
            self.assertTrue(servers["sfal-write"]["requires_approval"])
            self.assertTrue((ow / "mcp.json.bak").exists())
            self.assertTrue((ow / "skills" / "sf-log" / "SKILL.md").exists())

    def test_write_tools_exist(self):
        import asyncio
        from sfal import mcp_server
        names = {t.name for t in asyncio.run(mcp_server.server.list_tools())}
        self.assertLessEqual({"sfal_commit", "sfal_note_save", "sfal_setup_save_profile", "sfal_account_add"}, names)


if __name__ == "__main__":
    unittest.main()
